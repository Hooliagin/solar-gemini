import React, { useState, useRef } from 'react';
import { API_BASE_URL } from '../config';
import { supabase } from '../lib/supabase';
import { Mic, Square, Upload, Send, PenLine } from 'lucide-react';

interface RecorderProps {
    onUploadComplete: () => void;
}

const Recorder: React.FC<RecorderProps> = ({ onUploadComplete }) => {
    const [mode, setMode] = useState<'audio' | 'text'>('audio');
    const [isRecording, setIsRecording] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const [recordingTime, setRecordingTime] = useState(0);
    const [textInput, setTextInput] = useState('');
    const [isSending, setIsSending] = useState(false);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const chunksRef = useRef<Blob[]>([]);
    const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

    const startRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorderRef.current = new MediaRecorder(stream);
            chunksRef.current = [];

            mediaRecorderRef.current.ondataavailable = (e) => {
                if (e.data.size > 0) {
                    chunksRef.current.push(e.data);
                }
            };

            mediaRecorderRef.current.onstop = uploadAudio;
            mediaRecorderRef.current.start();
            setIsRecording(true);
            setRecordingTime(0);

            timerRef.current = setInterval(() => {
                setRecordingTime(t => t + 1);
            }, 1000);
        } catch (err) {
            console.error("Error accessing microphone:", err);
            alert("Microphone access denied.");
        }
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop();
            setIsRecording(false);
            mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());

            if (timerRef.current) {
                clearInterval(timerRef.current);
                timerRef.current = null;
            }
        }
    };

    const uploadAudio = async () => {
        setIsUploading(true);
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        const formData = new FormData();
        formData.append('file', blob, 'recording.webm');

        try {
            const token = (await supabase.auth.getSession()).data.session?.access_token;
            if (!token) throw new Error("No session");

            const response = await fetch(`${API_BASE_URL}/entries/upload`, {
                method: 'POST',
                headers: { Authorization: `Bearer ${token}` },
                body: formData,
            });

            if (response.ok) {
                onUploadComplete();
            } else {
                const errorData = await response.json();
                console.error("Upload failed:", errorData);
                alert(`Upload failed: ${errorData.detail}`);
            }
        } catch (error) {
            console.error("Upload error:", error);
            alert(`Error: ${(error as Error).message}`);
        } finally {
            setIsUploading(false);
            setRecordingTime(0);
        }
    };

    const sendText = async () => {
        if (!textInput.trim()) return;
        setIsSending(true);

        try {
            const token = (await supabase.auth.getSession()).data.session?.access_token;
            if (!token) throw new Error("No session");

            const response = await fetch(`${API_BASE_URL}/entries/text`, {
                method: 'POST',
                headers: {
                    Authorization: `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ text: textInput.trim() }),
            });

            if (response.ok) {
                setTextInput('');
                onUploadComplete();
            } else {
                const errorData = await response.json();
                console.error("Text submit failed:", errorData);
                alert(`Fehler: ${errorData.detail}`);
            }
        } catch (error) {
            console.error("Text submit error:", error);
            alert(`Fehler: ${(error as Error).message}`);
        } finally {
            setIsSending(false);
        }
    };

    const formatTime = (seconds: number) => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    };

    return (
        <div className="flex flex-col items-center justify-center h-full py-8">

            {/* Mode Toggle */}
            <div className="flex gap-1 mb-10 p-1 border border-charcoal/10 rounded-full">
                <button
                    onClick={() => setMode('audio')}
                    className={`flex items-center gap-2 px-5 py-2 rounded-full text-xs uppercase tracking-widest transition-all duration-300 ${mode === 'audio'
                            ? 'bg-charcoal text-white'
                            : 'text-charcoal/50 hover:text-charcoal'
                        }`}
                >
                    <Mic className="w-3.5 h-3.5" />
                    Audio
                </button>
                <button
                    onClick={() => setMode('text')}
                    className={`flex items-center gap-2 px-5 py-2 rounded-full text-xs uppercase tracking-widest transition-all duration-300 ${mode === 'text'
                            ? 'bg-charcoal text-white'
                            : 'text-charcoal/50 hover:text-charcoal'
                        }`}
                >
                    <PenLine className="w-3.5 h-3.5" />
                    Text
                </button>
            </div>

            {mode === 'audio' ? (
                /* Audio Mode */
                <>
                    <div className="relative mb-12">
                        {isRecording && (
                            <div className="absolute inset-0 rounded-full border border-red-500/20 animate-ping" />
                        )}

                        <button
                            onClick={isRecording ? stopRecording : startRecording}
                            disabled={isUploading}
                            className={`w-24 h-24 rounded-full flex items-center justify-center transition-all duration-500 outline-none ${isRecording
                                ? 'bg-red-600 shadow-xl scale-110'
                                : 'bg-charcoal hover:bg-black group'
                                } disabled:opacity-50 disabled:cursor-not-allowed`}
                        >
                            {isUploading ? (
                                <Upload className="w-8 h-8 text-white animate-bounce" />
                            ) : isRecording ? (
                                <Square className="w-8 h-8 text-white fill-current" />
                            ) : (
                                <Mic strokeWidth={1} className="w-8 h-8 text-white group-hover:scale-110 transition-transform duration-500" />
                            )}
                        </button>
                    </div>

                    <div className="text-center space-y-2 h-16">
                        {isRecording ? (
                            <>
                                <p className="text-4xl font-serif text-charcoal tabular-nums">
                                    {formatTime(recordingTime)}
                                </p>
                                <div className="flex items-center justify-center gap-2 text-red-500 text-xs uppercase tracking-widest animate-pulse">
                                    <div className="w-2 h-2 rounded-full bg-red-500" />
                                    Aufnahme läuft
                                </div>
                            </>
                        ) : isUploading ? (
                            <p className="text-xs uppercase tracking-widest text-charcoal animate-pulse">
                                Hochladen & Verarbeiten...
                            </p>
                        ) : (
                            <>
                                <p className="text-warm-grey font-serif italic text-lg">
                                    Tippen zum Aufnehmen.
                                </p>
                                <p className="text-[10px] uppercase tracking-widest text-charcoal/40">
                                    Automatisch transkribiert
                                </p>
                            </>
                        )}
                    </div>

                    {/* Visualizer */}
                    {isRecording && (
                        <div className="mt-8 flex gap-1 items-center h-8">
                            {[...Array(12)].map((_, i) => (
                                <div
                                    key={i}
                                    className="w-1 bg-charcoal/20 rounded-full animate-wave"
                                    style={{
                                        height: `${Math.random() * 100}%`,
                                        animationDelay: `${i * 0.1}s`
                                    }}
                                />
                            ))}
                        </div>
                    )}
                </>
            ) : (
                /* Text Mode */
                <div className="w-full max-w-md space-y-4">
                    <textarea
                        value={textInput}
                        onChange={(e) => setTextInput(e.target.value)}
                        placeholder="Schreibe deine Gedanken auf..."
                        rows={5}
                        className="w-full bg-transparent border border-charcoal/15 rounded-lg p-4 text-charcoal font-serif text-base leading-relaxed resize-none focus:outline-none focus:border-gold/60 transition-colors placeholder:text-charcoal/30 placeholder:italic"
                    />
                    <div className="flex items-center justify-between">
                        <p className="text-[10px] uppercase tracking-widest text-charcoal/40">
                            {textInput.length} Zeichen
                        </p>
                        <button
                            onClick={sendText}
                            disabled={isSending || !textInput.trim()}
                            className="flex items-center gap-2 px-6 py-2.5 bg-charcoal text-white rounded-full text-xs uppercase tracking-widest hover:bg-black transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                        >
                            {isSending ? (
                                <Upload className="w-3.5 h-3.5 animate-bounce" />
                            ) : (
                                <Send className="w-3.5 h-3.5" />
                            )}
                            {isSending ? 'Senden...' : 'Absenden'}
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Recorder;
