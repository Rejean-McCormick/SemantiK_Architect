// architect_frontend/src/app/refiner/page.tsx
'use client';

import { useState, useEffect } from 'react';
// [UPDATE] Import canonical client and config
import { architectApi, API_BASE_URL, Language } from '@/lib/api';

export default function RefinerPage() {
  const [languages, setLanguages] = useState<Language[]>([]);
  const [lang, setLang] = useState('zul');
  const [instructions, setInstructions] = useState('');
  const [status, setStatus] = useState('');

  useEffect(() => {
    // [UPDATE] Use the unified client to fetch languages
    const loadData = async () => {
        try {
            const data = await architectApi.listLanguages();
            setLanguages(data);
        } catch(e) {
            console.error("Failed to load languages", e);
        }
    };
    loadData();
  }, []);

  const handleRefine = async () => {
    setStatus('Sending request...');
    try {
      const selectedName = languages.find(l => l.code === lang)?.name || lang;
      
      // [UPDATE] Use native fetch + canonical API_BASE_URL
      // This ensures we hit http://localhost:8000/api/v1/grammar/refine (or the Docker equivalent)
      const res = await fetch(`${API_BASE_URL}/grammar/refine`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            lang: lang,
            lang_name: selectedName,
            instructions: instructions
        })
      });

      const data = await res.json();

      if (!res.ok) {
         throw new Error(data.detail || 'Request failed');
      }
      
      setStatus(`✅ Success: ${data.message}`);
    } catch (err: any) {
      setStatus(`❌ Error: ${err.message}`);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="bg-slate-900 border border-slate-800 p-6 rounded-lg shadow-xl">
        <h1 className="text-2xl font-bold text-purple-400 mb-2">🤖 AI Grammar Refiner</h1>
        <p className="text-slate-400 mb-6">Use this tool to upgrade a language from "Pidgin" (Tier 3) to "Fluent" (Tier 2) using LLMs.</p>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Target Language</label>
            <select value={lang} onChange={(e) => setLang(e.target.value)} className="w-full bg-slate-950 border border-slate-700 rounded p-2 text-slate-200">
               {languages.map(l => <option key={l.code} value={l.code}>{l.name} ({l.code})</option>)}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Instructions (Optional)</label>
            <textarea 
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              placeholder="e.g. 'Fix the word order for adjectives' or 'Add noun classes'"
              className="w-full h-32 bg-slate-950 border border-slate-700 rounded p-2 text-slate-200"
            />
          </div>

          <button onClick={handleRefine} className="w-full py-3 bg-purple-600 hover:bg-purple-500 text-white rounded font-bold shadow-lg shadow-purple-900/20 transition-all">
            Start Refinement Job 🚀
          </button>

          {status && (
            <div className={`p-4 rounded border text-sm ${status.startsWith('✅') ? 'bg-green-950/30 border-green-900 text-green-300' : 'bg-slate-950 border-slate-800 text-slate-300'}`}>
              {status}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}