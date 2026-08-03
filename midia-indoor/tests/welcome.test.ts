import { describe, expect, it, vi } from "vitest";
import { chooseWelcomeMessage, displayDuration, sanitizeDisplayName } from "@/lib/welcome";
import { entrySchema } from "@/lib/schemas";

describe("boas-vindas",()=>{
  it("mantém o nome completo e remove marcação insegura",()=>{expect(sanitizeDisplayName("  <Lázaro> Fernandes  ")).toBe("Lázaro Fernandes");});
  it("preenche o nome completo na mensagem padrão",()=>{expect(chooseWelcomeMessage("Mariana Souza","Bom treino, {nome}!",[],false)).toBe("Bom treino, Mariana Souza!");});
  it("reduz o tempo quando a fila atinge o limite",()=>{expect(displayDuration(8,15,8,7)).toBe(7);expect(displayDuration(7,15,8,7)).toBe(15);});
  it("pode sortear uma mensagem alternativa",()=>{vi.spyOn(Math,"random").mockReturnValue(.99);expect(chooseWelcomeMessage("Ana Lima","Olá, {nome}!",["Hoje é dia de evoluir, {nome}!"],true)).toBe("Hoje é dia de evoluir, Ana Lima!");vi.restoreAllMocks();});
});

describe("webhook",()=>{it("aceita o payload documentado",()=>{expect(entrySchema.safeParse({studentId:"12345",name:"Lázaro Fernandes",enteredAt:"2026-07-31T10:30:00-03:00",unitId:"ct-italo-vieira"}).success).toBe(true);});it("recusa data sem fuso",()=>{expect(entrySchema.safeParse({studentId:"1",name:"Aluno Teste",enteredAt:"2026-07-31T10:30:00",unitId:"ct-italo-vieira"}).success).toBe(false);});});
