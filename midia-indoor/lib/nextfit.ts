type NextFitClient = { id: number; nome?: string; dataNascimento?: string; inativo?: boolean|string; foto?: string };
type NextFitContract = { codigoCliente?: number; status?: string; dataInicio?: string; dataValidade?: string; dataEncerramento?: string; dataBloqueio?: string; dataSuspensao?: string };

export async function fetchEligibleBirthdays() {
  const apiKey = process.env.NEXTFIT_API_KEY; const baseUrl = process.env.NEXTFIT_BASE_URL; const version = process.env.NEXTFIT_API_VERSION || "1";
  if (!apiKey || !baseUrl) throw new Error("NEXTFIT_API_KEY e NEXTFIT_BASE_URL não configurados");
  const [clients, contracts] = await Promise.all([paginate<NextFitClient>(`${baseUrl.replace(/\/$/,"")}/api/v${version}/Pessoa/GetClientes`, apiKey), paginate<NextFitContract>(`${baseUrl.replace(/\/$/,"")}/api/v${version}/ContratoCliente`, apiKey)]);
  const today = new Date(); const active = new Set<number>(); const recent = new Map<number,NextFitContract>();
  for (const contract of contracts) { if (!contract.codigoCliente) continue; const current = recent.get(contract.codigoCliente); if (!current || dateValue(contract.dataInicio) > dateValue(current.dataInicio)) recent.set(contract.codigoCliente,contract); if (contract.status === "Ativo") active.add(contract.codigoCliente); }
  const todayKey = birthdayKey(new Date());
  return clients.filter((client) => {
    if (!client.dataNascimento || !client.nome || birthdayKey(client.dataNascimento) !== todayKey) return false; if (!isInactive(client.inativo) && active.has(client.id)) return true;
    const contract = recent.get(client.id); if (!contract || ["Agendado","Cancelado","Erro","Suspenso"].includes(contract.status||"")) return false; const validity=parseDate(contract.dataValidade); if (!validity) return false;
    if ([contract.dataEncerramento,contract.dataBloqueio,contract.dataSuspensao].some((value)=>{const date=parseDate(value);return date&&date<validity;})) return false;
    const days=Math.floor((startOfDay(today).getTime()-startOfDay(validity).getTime())/86_400_000); return days>=0&&days<=3;
  }).map((client)=>({ externalId:String(client.id), name:client.nome!.trim(), birthDate:new Date(client.dataNascimento!), photoUrl:client.foto||null }));
}

async function paginate<T>(url:string,apiKey:string) { const result:T[]=[]; let skip=0; while(true){const response=await fetch(`${url}?Skip=${skip}&Take=100`,{headers:{"X-Api-Key":apiKey,Accept:"application/json"},cache:"no-store",signal:AbortSignal.timeout(60_000)});if(!response.ok)throw new Error(`NextFit respondeu HTTP ${response.status}`);const data=await response.json() as {items?:T[];temProximaPagina?:boolean};result.push(...(data.items||[]));if(!data.temProximaPagina)break;skip+=100;}return result; }
function parseDate(value?:string){if(!value)return null;const date=new Date(value);return Number.isNaN(date.getTime())?null:date;}
function dateValue(value?:string){return parseDate(value)?.getTime()||0;}
function startOfDay(date:Date){return new Date(date.getFullYear(),date.getMonth(),date.getDate());}
function isInactive(value:unknown){return value===true||["TRUE","VERDADEIRO","1"].includes(String(value||"").toUpperCase());}
function birthdayKey(value:Date|string){if(typeof value==="string"){const match=/^\d{4}-(\d{2})-(\d{2})/.exec(value);if(match)return `${match[1]}/${match[2]}`;value=new Date(value);}return new Intl.DateTimeFormat("en-US",{month:"2-digit",day:"2-digit",timeZone:"America/Sao_Paulo"}).format(value);}
