import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Personal Finance Workbench",
  description: "Ruang kerja keuangan pribadi dan kantor.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="id">
      <body>{children}</body>
    </html>
  );
}
