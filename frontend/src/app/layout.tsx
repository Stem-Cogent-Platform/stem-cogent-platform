import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://stem-cogent.com"),
  applicationName: "Stem Cogent",
  title: {
    default: "Stem Cogent | Decision Intelligence for Nigerian Fintech",
    template: "%s · Stem Cogent"
  },
  description:
    "Evidence-backed decision intelligence for Nigerian fintech leaders, with verified signals, contextual briefs, and auditable recommendations.",
  alternates: { canonical: "/" },
  openGraph: {
    type: "website",
    url: "/",
    siteName: "Stem Cogent",
    title: "Stem Cogent | Decision Intelligence for Nigerian Fintech",
    description:
      "Verified signals, contextual briefs, and auditable recommendations for Nigerian fintech leaders."
  },
  twitter: {
    card: "summary",
    title: "Stem Cogent | Decision Intelligence for Nigerian Fintech",
    description:
      "Verified signals, contextual briefs, and auditable recommendations for Nigerian fintech leaders."
  },
  robots: { index: true, follow: true }
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
