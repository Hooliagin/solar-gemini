import React, { useState, useRef } from 'react';
import { API_BASE_URL } from '../config';

interface RecorderProps {
    onUploadComplete: () => void;
}

const Recorder: React.FC<RecorderProps> = ({ onUploadComplete }) => {
    const [isRecording, setIsRecording] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const chunksRef = useRef<Blob[]>([]);

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
        } catch (err) {
            console.error("Error accessing microphone:", err);
            alert("Microphone access denied or not available.");
        }
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop();
            setIsRecording(false);
            // Stop all tracks
            mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
        }
    };

    const uploadAudio = async () => {
        setIsUploading(true);
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        const formData = new FormData();
        formData.append('file', blob, 'recording.webm');

        try {
            const response = await fetch(`${API_BASE_URL}/entries/upload`, {
                method: 'POST',
                body: formData,
            });

            if (response.ok) {
                alert("Recording saved and transcribed!");
                onUploadComplete();
            } else {
                alert("Failed to upload recording.");
            }
        } catch (error) {
            console.error("Upload error:", error);
            alert("Error uploading file.");
        } finally {
            setIsUploading(false);
        }
    };

    return (
        <div className="flex flex-col items-center justify-center space-y-6">
            <div className={`w-48 h-48 rounded-full border-4 flex items-center justify-center transition-all duration-300 ${isRecording ? 'border-red-500 animate-pulse bg-red-900/20' : 'border-blue-500 bg-blue-900/20'}`}>
                {isRecording ? (
                    <div className="w-16 h-16 bg-red-500 rounded sm:rounded-md" />
                ) : (
                    <div className="text-4xl">🎙️</div>
                )}
            </div>

            <button
                onClick={isRecording ? stopRecording : startRecording}
                disabled={isUploading}
                className={`px-8 py-4 rounded-full text-xl font-bold transition-transform active:scale-95 ${isRecording
                    ? 'bg-red-600 hover:bg-red-700'
                    : 'bg-blue-600 hover:bg-blue-700'
                    } disabled:opacity-50 disabled:cursor-not-allowed`}
            >
                {isUploading ? 'Uploading...' : isRecording ? 'Results' : 'Start Recording'}
            </button>

            {isRecording && <p className="text-gray-400 animate-pulse">Recording... Speak your day.</p>}
        </div>
    );
};

export default Recorder;
