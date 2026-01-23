import React, { useState, useRef } from 'react';
import { API_BASE_URL } from '../config';
import { supabase } from '../lib/supabase';
import { Mic, Square, Upload, Check } from 'lucide-react';

interface RecorderProps {
    onUploadComplete: () => void;
}

const Recorder: React.FC<RecorderProps> = ({ onUploadComplete }) => {
    const [isRecording, setIsRecording] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const [recordingTime, setRecordingTime] = useState(0);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const chunksRef = useRef<Blob[]>([]);
    const timerRef = useRef<NodeJS.Timeout | null>(null);

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

            // Start timer
            timerRef.current = setInterval(() => {
                setRecordingTime(t => t + 1);
            }, 1000);
        } catch (err) {
            console.error("Error accessing microphone:", err);
            alert("Mikrofon-Zugriff verweigert oder nicht verfügbar.");
        }
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop();
            setIsRecording(false);
            mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());

            // Stop timer
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
                alert("Fehler beim Hochladen.");
            }
        } catch (error) {
            console.error("Upload error:", error);
            alert("Fehler beim Hochladen.");
        } finally {
            setIsUploading(false);
            setRecordingTime(0);
        }
    };

    const formatTime = (seconds: number) => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    };

    return (
        <div className="flex flex-col items-center justify-center space-y-6 py-4">
            {/* Recording Visualization */}
            <div className="relative">
                {/* Outer ring */}
                <div className={`w-32 h-32 rounded-full flex items-center justify-center transition-all duration-500 ${isRecording
                        ? 'bg-gradient-to-br from-red-500/20 to-orange-500/20 border-2 border-red-500/50'
                        : 'bg-gradient-to-br from-blue-500/20 to-cyan-500/20 border-2 border-blue-500/30'
                    }`}>
                    {/* Inner circle */}
                    <div className={`w-24 h-24 rounded-full flex items-center justify-center transition-all duration-300 ${isRecording
                            ? 'bg-gradient-to-br from-red-500 to-orange-500 animate-pulse shadow-lg shadow-red-500/50'
                            : 'bg-gradient-to-br from-blue-500 to-cyan-500 shadow-lg shadow-blue-500/30'
                        }`}>
                        {isRecording ? (
                            <Square className="w-8 h-8 text-white" />
                        ) : isUploading ? (
                            <Upload className="w-8 h-8 text-white animate-bounce" />
                        ) : (
                            <Mic className="w-8 h-8 text-white" />
                        )}
                    </div>
                </div>

                {/* Recording pulse rings */}
                {isRecording && (
                    <>
                        <div className="absolute inset-0 rounded-full border-2 border-red-500/50 animate-ping" />
                        <div className="absolute inset-0 rounded-full border border-red-500/30 animate-pulse" style={{ animationDelay: '0.5s' }} />
                    </>
                )}
            </div>

            {/* Timer / Status */}
            <div className="text-center">
                {isRecording ? (
                    <div className="space-y-1">
                        <p className="text-3xl font-mono font-bold text-red-400">
                            {formatTime(recordingTime)}
                        </p>
                        <p className="text-sm text-gray-400 animate-pulse">
                            Aufnahme läuft...
                        </p>
                    </div>
                ) : isUploading ? (
                    <div className="flex items-center gap-2 text-blue-400">
                        <Upload className="w-4 h-4 animate-spin" />
                        <span>Wird hochgeladen...</span>
                    </div>
                ) : (
                    <p className="text-sm text-gray-500">
                        Klicke zum Aufnehmen
                    </p>
                )}
            </div>

            {/* Record Button */}
            <button
                onClick={isRecording ? stopRecording : startRecording}
                disabled={isUploading}
                className={`px-8 py-3 rounded-full font-semibold transition-all active:scale-95 flex items-center gap-2 ${isRecording
                        ? 'bg-gradient-to-r from-red-500 to-orange-500 hover:from-red-400 hover:to-orange-400 shadow-lg shadow-red-500/30'
                        : 'bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-400 hover:to-cyan-400 shadow-lg shadow-blue-500/30'
                    } disabled:opacity-50 disabled:cursor-not-allowed text-white`}
            >
                {isUploading ? (
                    <>
                        <Upload className="w-5 h-5" />
                        Hochladen...
                    </>
                ) : isRecording ? (
                    <>
                        <Square className="w-5 h-5" />
                        Stoppen
                    </>
                ) : (
                    <>
                        <Mic className="w-5 h-5" />
                        Aufnahme starten
                    </>
                )}
            </button>

            {/* Hint */}
            <p className="text-xs text-gray-600 text-center max-w-xs">
                Sprich über deinen Tag, Gedanken oder Pläne. Die Aufnahme wird automatisch transkribiert.
            </p>
        </div>
    );
};

export default Recorder;
