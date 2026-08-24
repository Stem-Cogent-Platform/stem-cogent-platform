import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Stem", template: "%s · Stem" },
  description: "Evidence-backed decision intelligence for Nigerian fintech leaders"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
