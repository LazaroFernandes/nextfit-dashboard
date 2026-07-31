import { describe, expect, it, vi } from "vitest";
import { chooseWelcomeMessage, displayDuration, firstName, sanitizeDisplayName } from "@/lib/welcome";
import { entrySchema } from "@/lib/schemas";

describe("boas-vindas",()=>{
  it("usa apenas o primeiro nome e remove marcação insegura",()=>{expect(firstName(sanitizeDisplayName("  <Lázaro> Fernandes  "))).toBe("Lázaro");});
  it("preenche o nome na mensagem padrão",()=>{expect(chooseWelcomeMessage("Mariana Souza","Bom treino, {nome}!",[],false)).toBe("Bom treino, Mariana!");});
  it("reduz o tempo quando a fila atinge o limite",()=>{expect(displayDuration(8,15,8,7)).toBe(7);expect(displayDuration(7,15,8,7)).toBe(15);});
  it("pode sortear uma mensagem alternativa",()=>{vi.spyOn(Math,"random").mockReturnValue(.99);expect(chooseWelcomeMessage("Ana Lima","Olá, {nome}!",["Hoje é dia de evoluir, {nome}!"],true)).toBe("Hoje é dia de evoluir, Ana!");vi.restoreAllMocks();});
});

describe("webhook",()=>{it("aceita o payload documentado",()=>{expect(entrySchema.safeParse({studentId:"12345",name:"Lázaro Fernandes",enteredAt:"2026-07-31T10:30:00-03:00",unitId:"ct-italo-vieira"}).success).toBe(true);});it("recusa data sem fuso",()=>{expect(entrySchema.safeParse({studentId:"1",name:"Aluno Teste",enteredAt:"2026-07-31T10:30:00",unitId:"ct-italo-vieira"}).success).toBe(false);});});
