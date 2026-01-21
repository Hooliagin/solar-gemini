import { useState } from 'react';
import Recorder from './components/Recorder';
import Player from './components/Player';

function App() {
  // Simple state for Current Mode: 'evening' (record) or 'morning' (listen)
  // Default to evening logic if it's PM? Manual toggle for now.
  const [mode, setMode] = useState<'evening' | 'morning'>('evening');

  return (
    <div className="min-h-screen bg-gray-900 text-white flex flex-col items-center p-4">
      <header className="w-full max-w-xl flex justify-between items-center py-6">
        <h1 className="text-xl font-bold tracking-wider text-gray-100">AUDIO<span className="text-blue-500">MANAGER</span></h1>

        <div className="bg-gray-800 rounded-full p-1 flex">
          <button
            onClick={() => setMode('evening')}
            className={`px-4 py-1 rounded-full text-sm font-medium transition-all ${mode === 'evening' ? 'bg-blue-600 text-white shadow-lg' : 'text-gray-400 hover:text-white'}`}
          >
            Evening
          </button>
          <button
            onClick={() => setMode('morning')}
            className={`px-4 py-1 rounded-full text-sm font-medium transition-all ${mode === 'morning' ? 'bg-orange-500 text-white shadow-lg' : 'text-gray-400 hover:text-white'}`}
          >
            Morning
          </button>
        </div>
      </header>

      <main className="flex-1 w-full max-w-xl flex flex-col items-center justify-center mt-8 mb-20">

        {mode === 'evening' ? (
          <div className="text-center space-y-8 animate-fade-in">
            <h2 className="text-4xl font-extralight mb-2">How was your day?</h2>
            <p className="text-gray-400 max-w-xs mx-auto">Record your thoughts, tasks, and plans for tomorrow.</p>
            <Recorder onUploadComplete={() => alert('Saved! Have a good night.')} />
          </div>
        ) : (
          <div className="text-center space-y-8 w-full animate-fade-in">
            <h2 className="text-4xl font-extralight mb-2 text-orange-200">Good Morning</h2>
            <p className="text-gray-400 max-w-xs mx-auto">Here is your briefing.</p>
            <Player />
          </div>
        )}

      </main>

      <footer className="text-xs text-gray-600">
        Powered by Gemini & OpenAI
      </footer>
    </div>
  );
}

export default App;
