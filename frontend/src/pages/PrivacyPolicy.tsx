import { Shield, Server, Globe } from 'lucide-react';

const PrivacyPolicy = () => {
    return (
        <div className="min-h-screen bg-stone-900 text-stone-100 p-8 flex justify-center">
            <div className="max-w-2xl w-full space-y-8">
                <div className="text-center space-y-4">
                    <Shield className="w-16 h-16 mx-auto text-emerald-500" />
                    <h1 className="text-3xl font-bold font-serif">Datenschutzerklärung</h1>
                    <p className="text-stone-400">Transparenz über deine Daten</p>
                </div>

                <div className="bg-stone-800/50 p-6 rounded-2xl border border-stone-700 space-y-6">
                    <section className="space-y-3">
                        <h2 className="text-xl font-semibold flex items-center gap-2">
                            <Server className="w-5 h-5 text-amber-500" />
                            Datenbank & Speicher
                        </h2>
                        <p className="text-stone-300 leading-relaxed">
                            Deine persönlichen Daten (Nutzerprofil, Journal-Einträge, Einstellungen) werden sicher in einer <strong>Supabase-Datenbank</strong> gespeichert.
                        </p>
                        <ul className="list-disc list-inside text-stone-400 ml-4">
                            <li>Anbieter: Supabase Inc.</li>
                            <li>Standort: <strong>Frankfurt, Deutschland (AWS eu-central-1)</strong></li>
                            <li>Sicherheit: Verschlüsselte Übertragung und Speicherung (Rest & Transit)</li>
                        </ul>
                    </section>

                    <section className="space-y-3">
                        <h2 className="text-xl font-semibold flex items-center gap-2">
                            <Globe className="w-5 h-5 text-blue-500" />
                            Hosting & Berechnung
                        </h2>
                        <p className="text-stone-300 leading-relaxed">
                            Die Anwendung selbst (Backend & Frontend) wird bei <strong>Render</strong> gehostet.
                        </p>
                        <ul className="list-disc list-inside text-stone-400 ml-4">
                            <li>Anbieter: Render Services Inc.</li>
                            <li>Standort: <strong>Oregon, USA (us-west)</strong></li>
                            <li>Hinweis: Hier findet die Datenverarbeitung zur Laufzeit statt (z.B. KI-Generierung). Es werden keine Daten dauerhaft bei Render gespeichert.</li>
                        </ul>
                    </section>

                    <section className="space-y-3">
                        <h2 className="text-xl font-semibold">Drittanbieter (KI & Integrationen)</h2>
                        <p className="text-stone-300">
                            Zur Bereitstellung der Funktionen nutzen wir folgende Dienste:
                        </p>
                        <ul className="list-disc list-inside text-stone-400 ml-4">
                            <li><strong>Google Gemini API:</strong> Zur Textgenerierung und Stimmenanalyse (USA).</li>
                            <li><strong>Notion API:</strong> Wenn du die Verbindung aktivierst, werden To-Dos an dein Notion-Konto gesendet.</li>
                            <li><strong>Telegram:</strong> Für den Bot-Zugriff (Server von Telegram).</li>
                        </ul>
                    </section>
                </div>

                <div className="text-center text-sm text-stone-500">
                    <p>Stand: Februar 2026</p>
                    <p>Dies ist ein privates Projekt von Joshua Kamradt.</p>
                </div>
            </div>
        </div>
    );
};

export default PrivacyPolicy;
