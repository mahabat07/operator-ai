import "./globals.css";

export const metadata = {
  title: "Operator AI",
  description: "AI Chief of Staff",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
