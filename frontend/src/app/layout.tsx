import "@mantine/core/styles.css";
import React from "react";
import { MantineProvider, ColorSchemeScript, mantineHtmlProps } from "@mantine/core";
import { theme } from "../theme";

export const metadata = {
  title: "FPL Manager of the Week",
  description: "Fantasy Premier League Manager of the Week",
};

export default function RootLayout({ children }: { children: any }) {
  return (
    <html lang="en" {...mantineHtmlProps}>
      <head>
        <ColorSchemeScript defaultColorScheme="dark" />
        <link rel="shortcut icon" href="/favicon.svg" />
        <meta
          name="viewport"
          content="minimum-scale=1, initial-scale=1, width=device-width, user-scalable=no"
        />
      </head>
      <body>
        <MantineProvider theme={theme} defaultColorScheme="dark">
          {children}
        </MantineProvider>
      </body>
    </html>
  );
}
