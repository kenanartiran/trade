import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Private Trading App MVP",
  description: "Private trading web app MVP with FastAPI backend",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
