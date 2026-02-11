# Egghead.AI Setup Instructions

## 📁 File Structure

```
your-project/
├── app/
│   ├── page.tsx              ← Replace with the new page.tsx
│   ├── layout.tsx            ← Keep your existing one
│   ├── globals.css           ← Keep your existing one
│   └── api/
│       └── chat/
│           └── route.ts      ← Create this file
├── main.py                   ← Create this file
├── package.json              ← Keep your existing one
└── README.md                 ← This file
```

## 🚀 Step-by-Step Setup

### 1. Install Frontend Dependencies (if not already)

```bash
npm install
# or
yarn install
```

### 2. Install Backend Dependencies

```bash
pip install fastapi uvicorn pydantic
```

### 3. Copy the Files

1. **Replace** `app/page.tsx` with the new `page.tsx` file
2. **Create** `app/api/chat/route.ts` with the `route.ts` file
3. **Create** `main.py` in your project root with the `main.py` file

### 4. Run the Backend (Terminal 1)

```bash
python main.py
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

### 5. Run the Frontend (Terminal 2)

```bash
npm run dev
```

You should see:
```
▲ Next.js 14.x.x
- Local:        http://localhost:3000
```

### 6. Open Your Browser

Go to: http://localhost:3000

## ✨ Features

- **Sidebar with conversation history** grouped by date (Today, Yesterday, Last 7 Days, Older)
- **Dynamic layout** - centered title that moves to top-left after first message
- **New Chat button** - start fresh conversations
- **Delete conversations** - hover over any conversation to see the × button
- **localStorage** - all conversations are saved automatically
- **Connected to FastAPI backend** - messages go through your Python backend

## 🧪 Testing

Try these messages:
- "Hello!" → Should get "I'm still learning, but I got your message!"
- "Tell me about UC Davis" → Should get "UC Davis is a great campus 🌳"

## 🔧 Troubleshooting

### Frontend shows "Error: could not reach backend"
- Make sure `python main.py` is running in a separate terminal
- Check that port 8000 is not being used by another process

### Port 3000 already in use
```bash
# Kill the process on port 3000
lsof -ti:3000 | xargs kill -9
# Or run on a different port
npm run dev -- -p 3001
```

### Port 8000 already in use
```bash
# Kill the process on port 8000
lsof -ti:8000 | xargs kill -9
# Or change the port in main.py
uvicorn.run(app, host="0.0.0.0", port=8001)
# And update route.ts to match
```

### Conversations not saving
- Check browser console for localStorage errors
- Try clearing localStorage: Open DevTools > Application > Local Storage > Delete

## 📝 Next Steps

Now that it's working, you can enhance the backend in `main.py`:
- Add the UC Davis resources from your game plan
- Integrate with Hugging Face models
- Add more sophisticated routing logic
- Connect to a database instead of localStorage

## 🎨 Keeping Your Colors

The new UI uses your exact colors:
- `#200E57` → `#3B1FA6` gradient background
- `#2A176B` for message bubbles and input
- Yellow (`#FFD700`) for branding
- White borders and text

All your original styling is preserved!
