import { NextResponse } from "next/server";
import { adminOrUnauthorized } from "@/lib/auth-api";
import { db } from "@/lib/db";
import { emitTvEvent } from "@/lib/events";
import { fetchEligibleBirthdays } from "@/lib/nextfit";

export async function POST() {
  const auth=await adminOrUnauthorized(); if("response" in auth)return auth.response;
  try { const records=await fetchEligibleBirthdays(); let created=0,updated=0; for(const row of records){const existing=await db.birthday.findFirst({where:{externalSource:"NEXTFIT",externalId:row.externalId}}); if(existing){await db.birthday.update({where:{id:existing.id},data:{name:row.name,birthDate:row.birthDate,photoUrl:row.photoUrl,active:true}});updated++;}else{await db.birthday.create({data:{...row,externalSource:"NEXTFIT",active:true}});created++;}} await db.auditLog.create({data:{adminUserId:auth.session.sub,action:"SYNC_NEXTFIT",entity:"Birthday",details:{created,updated,total:records.length}}});emitTvEvent({type:"playlist.reload"});return NextResponse.json({created,updated,total:records.length}); }
  catch(error){return NextResponse.json({error:error instanceof Error?error.message:"Falha na sincronização"},{status:502});}
}
