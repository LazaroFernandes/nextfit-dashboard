import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CT Ítalo Vieira | Mídia Indoor",
  description: "Mídia indoor, boas-vindas e aniversariantes do CT Ítalo Vieira",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="pt-BR"><body>{children}</body></html>;
}
