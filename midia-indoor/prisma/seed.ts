import { PrismaClient } from "@prisma/client";
import bcrypt from "bcryptjs";
import { hashSecret } from "../lib/security";

const db = new PrismaClient();
async function main() {
  const email=(process.env.INITIAL_ADMIN_EMAIL||"admin@ctitalovieira.com.br").toLowerCase(); const password=process.env.INITIAL_ADMIN_PASSWORD||"Admin123!Troque";
  await db.adminUser.upsert({where:{email},update:{},create:{email,name:"Administrador",passwordHash:await bcrypt.hash(password,12)}});
  await db.systemSettings.upsert({where:{id:"default"},update:{},create:{id:"default",tvTokenHash:hashSecret(process.env.TV_DISPLAY_TOKEN||"tv-demo-ctiv-2026"),entryApiKeyHash:hashSecret(process.env.ENTRY_API_KEY||"entry-demo-ctiv-2026")}});
  if(await db.sponsorMedia.count()===0) await db.sponsorMedia.createMany({data:[
    {name:"Aurora Performance",fileUrl:"/demo/sponsor-aurora.svg",type:"IMAGE",mimeType:"image/svg+xml",durationSec:10,sortOrder:1,sponsorName:"Aurora Performance"},
    {name:"Norte Nutrição",fileUrl:"/demo/sponsor-norte.svg",type:"IMAGE",mimeType:"image/svg+xml",durationSec:10,sortOrder:2,sponsorName:"Norte Nutrição"},
    {name:"CT Ítalo Vieira · Institucional",fileUrl:"/demo/institutional.svg",type:"IMAGE",mimeType:"image/svg+xml",durationSec:12,sortOrder:3},
  ]});
  if(await db.birthday.count()===0){const today=new Date();await db.birthday.createMany({data:[{name:"Mariana Souza",birthDate:new Date(Date.UTC(1994,today.getUTCMonth(),today.getUTCDate(),12)),message:"Hoje é aniversário da Mariana. Parabéns!",showLastName:false,externalSource:"DEMO"},{name:"Rafael Martins",birthDate:new Date(Date.UTC(1990,today.getUTCMonth(),today.getUTCDate(),12)),message:"Feliz aniversário e um treino incrível!",showLastName:true,externalSource:"DEMO"}]});}
  if(await db.entryEvent.count()===0){for(const [index,name] of ["Lázaro Fernandes","Camila Rocha","Bruno Lima","Ana Paula","Diego Alves"].entries()){const event=await db.entryEvent.create({data:{externalId:`demo-${index+1}`,studentName:name,enteredAt:new Date(Date.now()+index*1000),unitId:"ct-italo-vieira",source:"ADMIN"}});await db.welcomeQueue.create({data:{entryEventId:event.id,displayName:name.split(" ")[0],message:`Seja bem-vindo, ${name.split(" ")[0]}!`,expiresAt:new Date(Date.now()+60*60_000)}});}}
  console.log(`Seed concluído. Admin: ${email}`); if(!process.env.INITIAL_ADMIN_PASSWORD)console.log(`Senha de demonstração: ${password}`);
}
main().finally(()=>db.$disconnect());
