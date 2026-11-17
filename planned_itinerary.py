"""Plan ride visits using observed per-weekday wait estimates, and export PDF."""
from datetime import timedelta
from io import BytesIO
import pandas as pd
WEEKDAYS=('Segunda','Terça','Quarta','Quinta','Sexta','Sábado','Domingo')

def plan_ride_hours(profile, selected, catalog, day, park, buffer_min=20):
    """Non-overlapping approximate start slots; no invented wait estimates."""
    if profile is None or profile.empty:return [],list(selected)
    chosen=[];missing=[]
    occupied_until=-1
    # Schedule constrained rides first: fewest available hourly slots.
    groups={}
    for rid in selected:
        candidates=profile[profile['id'].astype(str)==str(rid)].sort_values(
            ['Fila típica (min)','Horário'])
        groups[rid]=candidates.to_dict('records')
    for rid in sorted(selected,key=lambda x:(len(groups[x]),x)):
        options=groups[rid]
        if not options:
            missing.append(rid);continue
        # Choose best available slot, keeping fixed buffer + predicted queue.
        used=[(r['start'],r['finish']) for r in chosen]
        viable=[]
        for item in options:
            start=int(item['Horário'][:2])*60+int(item['Horário'][3:])
            wait=float(item['Fila típica (min)'])
            finish=start+max(10,round(wait))+buffer_min
            if any(start<end and finish>begin for begin,end in used):continue
            viable.append((wait,start,finish,item))
        if not viable:
            missing.append(rid);continue
        wait,start,finish,item=min(viable,key=lambda v:(v[0],v[1]))
        chosen.append({'start':start,'finish':finish,'Data':day.strftime('%d/%m/%Y'),
                       'Dia':WEEKDAYS[day.weekday()],'Parque':park,
                       'Horário':f'{start//60:02d}:{start%60:02d}',
                       'Atração':catalog.get(rid,rid),
                       'Fila típica (min)':round(wait),
                       'Dias observados':int(item['Dias observados'])})
    chosen.sort(key=lambda r:r['start'])
    for row in chosen:row.pop('start');row.pop('finish')
    return chosen,missing

def optimize_ride_route(profile, selected, catalog, day, park, travel_minutes=None,
                        buffer_min=10, ride_duration_min=12, max_states=60, include_ids=False):
    """Beam-search over supported historical slots, waits and verified walking routes.

    travel_minutes maps (origin_id, destination_id) to minutes from a routing service.
    Missing routes are UNKNOWN, not zero-minute estimates; the scheduler uses the
    configured safety buffer but marks the walking portion as unverified.
    """
    import math
    travel_minutes=travel_minutes or {}
    rides=[str(r) for r in selected]
    if profile is None or profile.empty:return [],rides
    candidates={}
    for rid in rides:
        sub=profile[profile['id'].astype(str)==rid]
        options=[]
        for _,r in sub.iterrows():
            try:
                h,m=map(int,str(r['Horário']).split(':')[:2]); wait=float(r['Fila típica (min)'])
                days=int(r['Dias observados'])
            except (ValueError,TypeError,KeyError):continue
            if not math.isfinite(wait) or wait<0:continue
            options.append((h*60+m,wait,days))
        candidates[rid]=sorted(options)
    active=[rid for rid in rides if candidates[rid]]
    if not active:return [],rides
    first=min(t for rid in active for t,_,_ in candidates[rid])
    # state: (visits, finish_time, accumulated_wait, accumulated_walk, unknown_count, rows, last_id)
    beam=[(frozenset(),first,0.,0.,0,[],None)]
    best=beam[0]
    for _ in range(len(active)):
        successors=[]
        for visited,finish,wait_sum,walk_sum,unknown,rows,last in beam:
            for rid in active:
                if rid in visited:continue
                known=last is None or (last,rid) in travel_minutes
                walk=float(travel_minutes[(last,rid)]) if last is not None and known else None
                # Conservative buffer also applies when routing succeeds, for access/boarding.
                earliest=finish+(walk if walk is not None else 0)+buffer_min if last else finish
                for slot,wait,days in candidates[rid]:
                    start=math.ceil(max(slot,earliest))
                    # Each hourly observation is valid only until the next hour.
                    if start>=slot+60:continue
                    end=start+max(10,round(wait))+ride_duration_min
                    new_rows=rows+[{'_id':rid,'_start':start,'_finish':end,
                        'Data':day.strftime('%d/%m/%Y'),'Dia':WEEKDAYS[day.weekday()],
                        'Parque':park,'Horário':f'{start//60:02d}:{start%60:02d}',
                        'Atração':catalog.get(rid,rid),'Fila típica (min)':round(wait),
                        'Dias observados':days,'Caminhada (min)':round(walk,1) if walk is not None else None,
                        'Rota verificada':'Sim' if last is None or known else 'Não',
                        'Duração atração (min)':ride_duration_min}]
                    successors.append((visited|{rid},end,wait_sum+wait,
                                       walk_sum+(walk or 0),unknown+int(last is not None and not known),
                                       new_rows,rid))
        if not successors:break
        # Maximize completed attractions; then earliest finish, shortest waits/walks.
        successors.sort(key=lambda v:(v[1],v[2]+v[3],v[4]))
        # Deduplicate states with same visited set and last ride to preserve alternatives.
        seen=set(); beam=[]
        for state in successors:
            key=(state[0],state[6])
            if key in seen:continue
            seen.add(key);beam.append(state)
            if len(beam)>=max_states:break
        candidate=min(beam,key=lambda v:(v[1],v[2]+v[3],v[4]))
        if len(candidate[0])>len(best[0]) or (len(candidate[0])==len(best[0]) and
                                             (candidate[1],candidate[2]+candidate[3])<(best[1],best[2]+best[3])):
            best=candidate
    output=[]
    for r in best[5]:
        r=r.copy();
        if not include_ids:r.pop('_id')
        r.pop('_start');r.pop('_finish');output.append(r)
    missing=[rid for rid in rides if rid not in best[0]]
    return output,missing

def itinerary_pdf(assignments, rows, warnings=(), alternative=None):
    """Generate a basic, paginated A4 PDF with only Python's standard library."""
    from textwrap import wrap
    from datetime import date
    lines=['GUIA ORLANDO - ROTEIRO PLANEJADO',
           'Base: historico remoto ThemeParks.wiki. Filas nao garantidas.', '']
    if alternative is not None:lines.extend(['OPCAO 1 - MELHOR COMBINACAO',''])
    for park, day, avg, n in assignments:
        lines.append(f'{day:%d/%m/%Y} - {WEEKDAYS[day.weekday()]} - {park}')
        lines.append(f'Fila media historica do parque: {avg:.1f} min; dias observados: {n}')
        entries=[r for r in rows if r['Parque']==park and r['Data']==day.strftime('%d/%m/%Y')]
        if not entries:lines.append('Sem horarios com cobertura historica suficiente.')
        for r in entries:
            line=f"{r['Horário']}  {r['Atração']} - fila {r['Fila típica (min)']} min (amostra: {r['Dias observados']} dias)"
            if 'Caminhada (min)' in r:line+=(f"; caminhada: {r['Caminhada (min)']} min" if r['Caminhada (min)'] is not None else '; caminhada nao verificada')
            lines.extend(wrap(line,width=91,break_long_words=False,break_on_hyphens=False) or [''])
        lines.append('')
    if warnings:
        lines.append('OBSERVACOES - OPCAO 1')
        for warning in warnings:lines.extend(wrap(str(warning),width=91))
    if alternative is not None:
        alt_assignments,alt_rows,alt_warnings=alternative
        lines.extend(['', '='*55, 'OPCAO 2 - SEGUNDA MELHOR COMBINACAO', '='*55, ''])
        for park,day,avg,n in alt_assignments:
            lines.append(f'{day:%d/%m/%Y} - {WEEKDAYS[day.weekday()]} - {park}')
            lines.append(f'Fila media historica do parque: {avg:.1f} min; dias observados: {n}')
            entries=[r for r in alt_rows if r['Parque']==park and r['Data']==day.strftime('%d/%m/%Y')]
            if not entries:lines.append('Sem horarios com cobertura historica suficiente.')
            for r in entries:
                line=f"{r['Horário']}  {r['Atração']} - fila {r['Fila típica (min)']} min (amostra: {r['Dias observados']} dias)"
                if 'Caminhada (min)' in r:line+=(f"; caminhada: {r['Caminhada (min)']} min" if r['Caminhada (min)'] is not None else '; caminhada nao verificada')
                lines.extend(wrap(line,width=91,break_long_words=False,break_on_hyphens=False) or [''])
            lines.append('')
        if alt_warnings:
            lines.append('OBSERVACOES - OPCAO 2')
            for warning in alt_warnings:lines.extend(wrap(str(warning),width=91))
    lines.extend(['', 'Roteiro estimado. Confirme horarios, eventos e Lightning Lane.',
                  'Caminhadas somente quando rota verificada; trechos ausentes nao sao medidos.'])
    def pdf_text(value):
        # WinAnsi (Windows-1252) encoding supports Portuguese accents.
        raw=value.encode('cp1252','replace').decode('latin-1')
        return raw.replace('\\','\\\\').replace('(','\\(').replace(')','\\)')
    pages=[lines[i:i+56] for i in range(0,len(lines),56)] or [[]]
    objects=[]
    def add(data):objects.append(data);return len(objects)
    catalog=add('')
    pages_root=add('')
    font=add('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>')
    page_ids=[]
    for page in pages:
        commands=['BT','/F1 10 Tf','40 805 Td','13 TL']
        for line in page:
            commands.append(f'({pdf_text(line)}) Tj')
            commands.append('T*')
        commands.append('ET')
        stream='\n'.join(commands).encode('latin-1')
        stream_id=add(b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream')
        page_id=add(f'<< /Type /Page /Parent {pages_root} 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 {font} 0 R >> >> /Contents {stream_id} 0 R >>')
        page_ids.append(page_id)
    objects[pages_root-1]='<< /Type /Pages /Kids ['+' '.join(f'{x} 0 R' for x in page_ids)+f'] /Count {len(page_ids)} >>'
    objects[catalog-1]=f'<< /Type /Catalog /Pages {pages_root} 0 R >>'
    result=bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
    offsets=[0]
    for i,obj in enumerate(objects,1):
        offsets.append(len(result))
        if isinstance(obj,str):obj=obj.encode('latin-1')
        result.extend(f'{i} 0 obj\n'.encode()+obj+b'\nendobj\n')
    xref=len(result)
    result.extend(f'xref\n0 {len(objects)+1}\n0000000000 65535 f \n'.encode())
    for off in offsets[1:]:result.extend(f'{off:010d} 00000 n \n'.encode())
    result.extend(f'trailer\n<< /Size {len(objects)+1} /Root {catalog} 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode())
    return bytes(result)
