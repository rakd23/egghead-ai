export default function LoginPage() {
  return (
    <div className="flex h-screen bg-gradient-to-b from-[#0F2A54] via-[#0B1E3D] to-[#001426] text-white items-center justify-center">
      <div className="flex flex-col items-center gap-6 text-center">
        <img
          src="/Egghead Logo.png"
          alt="Egghead logo"
          className="w-52 h-52 object-contain mix-blend-screen"
        />
        <h1 className="text-5xl font-bold text-yellow-400">Egghead.AI</h1>
        <p className="text-white/50">Your UC Davis campus assistant 🐄</p>
        <a
          href="/auth/login"
          className="mt-4 px-8 py-3 bg-yellow-400 hover:bg-yellow-500 text-[#0B1E3D] font-bold rounded-full transition-colors text-lg"
        >
          Sign in with UC Davis Google
        </a>
        <p className="text-white/30 text-sm">Only @ucdavis.edu emails are allowed</p>
      </div>
    </div>
  );
}