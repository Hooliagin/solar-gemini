
import { ScrollText, CheckCircle, AlertCircle } from 'lucide-react';

const TermsOfService = () => {
    return (
        <div className="min-h-screen bg-stone-900 text-stone-100 p-8 flex justify-center">
            <div className="max-w-2xl w-full space-y-8">
                <div className="text-center space-y-4">
                    <ScrollText className="w-16 h-16 mx-auto text-amber-500" />
                    <h1 className="text-3xl font-bold font-serif">Nutzungsbedingungen</h1>
                    <p className="text-stone-400">Terms of Service</p>
                </div>

                <div className="bg-stone-800/50 p-6 rounded-2xl border border-stone-700 space-y-6">
                    <section className="space-y-3">
                        <h2 className="text-xl font-semibold flex items-center gap-2">
                            <CheckCircle className="w-5 h-5 text-emerald-500" />
                            1. Leistungsbeschreibung
                        </h2>
                        <p className="text-stone-300 leading-relaxed">
                            Der "Daily Manager Bot" ist ein persönlicher KI-Assistent, der entwickelt wurde, um tägliche Aufgaben, Kalendertermine und Notizen zu verwalten.
                        </p>
                        <ul className="list-disc list-inside text-stone-400 ml-4">
                            <li>Verarbeitung von Sprachnachrichten via Telegram.</li>
                            <li>Synchronisation mit Google Calendar und Notion.</li>
                            <li>Generierung von täglichen Briefings (Text & Audio).</li>
                        </ul>
                    </section>

                    <section className="space-y-3">
                        <h2 className="text-xl font-semibold flex items-center gap-2">
                            <AlertCircle className="w-5 h-5 text-red-400" />
                            2. Haftungsausschluss
                        </h2>
                        <p className="text-stone-300 leading-relaxed">
                            Dieser Dienst wird privat "wie besehen" (as is) zur Verfügung gestellt. Es gibt keine Garantie für:
                        </p>
                        <ul className="list-disc list-inside text-stone-400 ml-4">
                            <li>Lückenlose Verfügbarkeit des Dienstes.</li>
                            <li>Fehlerfreiheit der KI-Generierungen (Halluzinationen möglich).</li>
                            <li>Dauerhafte Speicherung der Daten (Backups empfohlen).</li>
                        </ul>
                    </section>

                    <section className="space-y-3">
                        <h2 className="text-xl font-semibold">3. Nutzung von Drittanbieter-Diensten</h2>
                        <p className="text-stone-300">
                            Durch die Verbindung Ihres Notion- oder Google-Kontos gestatten Sie der Anwendung, in Ihrem Namen Lese- und Schreibzugriffe durchzuführen, wie im Consent-Screen beschrieben.
                        </p>
                    </section>

                    <section className="space-y-3">
                        <h2 className="text-xl font-semibold">4. Beendigung</h2>
                        <p className="text-stone-300">
                            Sie können die Nutzung jederzeit beenden, indem Sie die Verbindungen in den Einstellungen trennen und den Telegram-Bot blockieren.
                        </p>
                    </section>
                </div>

                <div className="text-center text-sm text-stone-500">
                    <p>Stand: Februar 2026</p>
                    <p>Kontakt: Joshua Kamradt</p>
                </div>
            </div>
        </div>
    );
};

export default TermsOfService;
