# Guia Orlando v61 — Caminhadas bidirecionais

O cálculo de rotas a pé consulta Valhalla nos dois sentidos e usa a menor distância válida. Quando a rota inversa é escolhida, a geometria é invertida para exibição da origem ao destino selecionados. A escolha é uma correção heurística para sentidos incorretos nos dados OSM; não confirma autorização para transitar por caminhos de mão única ou restritos.

O arquivo de cache de rotas agora é `walking_routes_v61.sqlite3`, criado automaticamente. Isso invalida tempos anteriores calculados em apenas um sentido. Os demais caches, contas, Supabase e histórico permanecem inalterados.

O tempo é calculado com a velocidade de caminhada configurada. A API pode falhar ou retornar rotas indisponíveis; nesses casos, o aplicativo não inventa distâncias.
