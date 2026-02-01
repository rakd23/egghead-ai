export default function Home() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-b from-[#200E57] to-[#3B1FA6] text-white">
      <h1 className="text-5xl font-semibold mb-8 text-yellow-400">
        Egghead.AI
      </h1>

      <div className="flex items-center w-[600px] max-w-full bg-[#2A176B] border border-white/30 rounded-full px-4 py-3">
        <input
          type="text"
          placeholder="Ask anything, Aggie..."
          className="flex-1 bg-transparent outline-none text-white placeholder-yellow-300"
        />

        <button className="ml-3 w-10 h-10 rounded-full bg-yellow-400 flex items-center justify-center text-[#200E57] font-bold">
          ↑
        </button>
      </div>
    </main>
  );
}
