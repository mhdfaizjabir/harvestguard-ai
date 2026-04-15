import "./globals.css";

export const metadata = {
  title: "HarvestGuard AI | Hyperbloom V2",
  description:
    "SDG 2 crop-stress early warning dashboard with live climate signals, explainable ML scoring, forecasting, scenario modeling, and intervention briefs.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body>{children}</body>
    </html>
  );
}
