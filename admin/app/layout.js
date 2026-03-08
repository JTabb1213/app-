import "./globals.css";

export const metadata = {
    title: "Crypto Admin Dashboard",
    description: "Admin panel for managing cryptocurrency data and cache",
};

export default function RootLayout({ children }) {
    return (
        <html lang="en">
            <body>{children}</body>
        </html>
    );
}
