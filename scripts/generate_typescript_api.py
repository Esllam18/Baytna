import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; spec=json.loads((ROOT/'contracts/openapi.json').read_text(encoding='utf-8')); paths=spec.get('paths',{}); out=ROOT/'apps/customer_app/src/generated/openapi.ts'; out.parent.mkdir(parents=True,exist_ok=True); lines=['/* Auto-generated from Baytna OpenAPI. */','export const apiRoutes = {'];
for path in sorted(paths):
    methods=[m.upper() for m in paths[path] if m.lower() in {'get','post','put','patch','delete'}]; key=path.replace('/','_').replace('{','').replace('}','').strip('_').replace('-','_'); lines.append(f'  {key!r}: {{ path: {path!r}, methods: {methods!r} }},')
lines += ['} as const;',f'export const openApiPathCount = {len(paths)} as const;']; out.write_text('\n'.join(lines)+'\n',encoding='utf-8'); print(f'Generated {len(paths)} routes.')
