"""Per-user Supabase Auth and PostgREST settings, protected by RLS.
Only whitelisted search parameters are persisted; never itineraries or API data.
"""
import json
import time
import requests

TIMEOUT=12

def config():
    import streamlit as st
    try:
        url=str(st.secrets['SUPABASE_URL']).rstrip('/')
        key=str(st.secrets['SUPABASE_ANON_KEY'])
        if not url.startswith('https://') or not key: return None
        return url,key
    except (KeyError,FileNotFoundError): return None

def headers(token=None):
    url,key=config()
    return {'apikey':key,'Authorization':'Bearer '+(token or key),'Content-Type':'application/json'}

def auth_call(endpoint, payload):
    url,_=config()
    r=requests.post(url+'/auth/v1/'+endpoint,json=payload,headers=headers(),timeout=TIMEOUT)
    if r.status_code>=400:
        try: message=r.json().get('msg') or r.json().get('error_description') or r.json().get('message')
        except ValueError: message=None
        raise ValueError(message or 'Não foi possível autenticar. Confira os dados e tente novamente.')
    return r.json()

def ensure_token(state):
    if not state.get('_auth_access'): return False
    if time.time() < state.get('_auth_expires',0)-120: return True
    try:
        data=auth_call('token?grant_type=refresh_token',{'refresh_token':state['_auth_refresh']})
        assign_tokens(state,data)
        return True
    except (requests.RequestException,ValueError,KeyError):
        logout(state)
        return False

def assign_tokens(state,data):
    if not data.get('access_token') or not data.get('user',{}).get('id'):
        raise ValueError('Verifique seu e-mail para confirmar a conta antes de entrar.')
    state['_auth_access']=data['access_token']
    state['_auth_refresh']=data['refresh_token']
    state['_auth_expires']=time.time()+int(data.get('expires_in',3600))
    state['_auth_user']=data['user']['id']
    state['_auth_email']=data['user'].get('email','')
    state.pop('_auth_loaded',None)
    state.pop('_auth_last_hash',None)

def logout(state):
    # Clear the whole Streamlit session so another account never inherits widgets.
    for k in list(state): del state[k]

def gate(state):
    import streamlit as st
    if not config():
        st.error('Login não configurado. Configure SUPABASE_URL e SUPABASE_ANON_KEY em App settings → Secrets.')
        st.stop()
    if ensure_token(state):
        with st.sidebar:
            st.caption('Conta: '+state.get('_auth_email',''))
            if st.button('Sair da conta',key='_auth_logout'):
                logout(state)
                st.rerun()
        return
    st.title('🎢 Guia Orlando')
    st.write('Entre para manter os parâmetros das suas pesquisas sincronizados entre celular e computador.')
    tab_login,tab_signup=st.tabs(['Entrar','Criar conta'])
    with tab_login:
        with st.form('_auth_login_form'):
            email=st.text_input('E-mail',key='_login_email')
            password=st.text_input('Senha',type='password',key='_login_pass')
            submit=st.form_submit_button('Entrar',use_container_width=True)
        if submit:
            try:
                assign_tokens(state,auth_call('token?grant_type=password',{'email':email.strip(),'password':password}))
                st.rerun()
            except (requests.RequestException,ValueError,KeyError) as exc: st.error(str(exc))
    with tab_signup:
        with st.form('_auth_signup_form'):
            new_email=st.text_input('Seu e-mail',key='_signup_email')
            new_password=st.text_input('Crie uma senha (mínimo 8 caracteres)',type='password',key='_signup_pass')
            create=st.form_submit_button('Criar conta',use_container_width=True)
        if create:
            if len(new_password)<8: st.error('Use uma senha com pelo menos 8 caracteres.')
            else:
                try:
                    auth_call('signup',{'email':new_email.strip(),'password':new_password})
                    st.success('Cadastro solicitado. Se a confirmação de e-mail estiver ativa, confirme o e-mail e depois entre.')
                except (requests.RequestException,ValueError) as exc: st.error(str(exc))
    st.caption('Os parâmetros são armazenados na sua conta. Resultados de filas e roteiros não são salvos.')
    st.stop()

def load(state, allowed, deserialize):
    import streamlit as st
    if state.get('_auth_loaded') or not ensure_token(state): return
    url,_=config()
    try:
        r=requests.get(url+'/rest/v1/user_search_params',params={'select':'params','user_id':'eq.'+state['_auth_user']},headers=headers(state['_auth_access']),timeout=TIMEOUT)
        r.raise_for_status()
        items=r.json()
        if items:
            for k,v in items[0]['params'].items():
                if allowed(k) and k not in state:
                    try: state[k]=deserialize(v)
                    except (ValueError,TypeError,KeyError): pass
        state['_auth_loaded']=True
    except (requests.RequestException,ValueError,KeyError) as exc:
        st.warning('Não foi possível recuperar as preferências da nuvem: '+str(exc))

def save(state, allowed, serialize):
    import streamlit as st
    if not ensure_token(state): return
    params={}
    for k in list(state):
        if allowed(k):
            try: params[k]=serialize(state[k])
            except (TypeError,ValueError): pass
    payload=json.dumps(params,sort_keys=True,ensure_ascii=False)
    if payload==state.get('_auth_last_hash'): return
    url,_=config()
    try:
        r=requests.post(url+'/rest/v1/user_search_params',headers={**headers(state['_auth_access']),'Prefer':'resolution=merge-duplicates'},json={'user_id':state['_auth_user'],'params':params},timeout=TIMEOUT)
        r.raise_for_status()
        state['_auth_last_hash']=payload
    except requests.RequestException as exc:
        # No false claim of persistence; retry on next rerun.
        st.warning('Não foi possível salvar as preferências na nuvem: '+str(exc))

def clear(state, allowed):
    import streamlit as st
    if not ensure_token(state): return
    url,_=config()
    try:
        r=requests.delete(url+'/rest/v1/user_search_params',params={'user_id':'eq.'+state['_auth_user']},headers=headers(state['_auth_access']),timeout=TIMEOUT)
        r.raise_for_status()
        state.pop('_auth_last_hash',None)
    except requests.RequestException as exc:
        st.error('Falha ao limpar as preferências na nuvem: '+str(exc))
