# Egghead.AI Setup Instructions

## Project Structure

```
your-project/
├── app/
│   ├── page.tsx              # Replace with the new page.tsx
│   ├── layout.tsx            # Keep existing file
│   ├── globals.css           # Keep existing file
│   └── api/
│       └── chat/
│           └── route.ts      # Create this file
├── main.py                   # FastAPI backend
├── package.json              # Frontend dependencies
└── README.md
```

---

# Setup

## 1. Install Frontend Dependencies

If dependencies are not installed:

```
npm install
```

or

```
yarn install
```

---

## 2. Install Backend Dependencies

Install the required Python packages:

```
pip install fastapi uvicorn pydantic
```

---

## 3. Copy Required Files

Make the following changes to your project:

* Replace `app/page.tsx` with the updated `page.tsx`
* Create `app/api/chat/route.ts` using the provided `route.ts`
* Create `main.py` in the project root using the provided backend code

---

## 4. Start the Backend

Run the FastAPI server:

```
python main.py
```

Expected output:

```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

---

## 5. Start the Frontend

In a separate terminal:

```
npm run dev
```

Expected output:

```
Next.js
Local: http://localhost:3000
```

---

## 6. Open the Application

Navigate to:

```
http://localhost:3000
```

---

# Features

* Conversation history grouped by date (Today, Yesterday, Last 7 Days, Older)
* Dynamic interface: title moves after the first message
* New chat creation
* Conversation deletion
* Persistent conversations stored in `localStorage`
* Integration with a FastAPI backend for message handling

---

# Testing

Example test messages:

```
Hello!
```

Expected response:

```
I'm still learning, but I received your message.
```

```
Tell me about UC Davis
```

Expected response:

```
UC Davis is a major public research university in California.
```

---

# Troubleshooting

## Frontend Cannot Reach Backend

Ensure the backend server is running:

```
python main.py
```

Also confirm that port `8000` is not already in use.

---

## Port 3000 Already in Use

Kill the existing process:

```
lsof -ti:3000 | xargs kill -9
```

Or run the frontend on a different port:

```
npm run dev -- -p 3001
```

---

## Port 8000 Already in Use

Terminate the process using the port:

```
lsof -ti:8000 | xargs kill -9
```

Or change the port in `main.py`:

```
uvicorn.run(app, host="0.0.0.0", port=8001)
```

If the port changes, update the API endpoint in `route.ts`.

---

## Conversations Not Saving

Check the browser console for `localStorage` errors.

You may need to clear stored data:

1. Open browser developer tools
2. Navigate to the **Application** tab
3. Select **Local Storage**
4. Remove existing entries

---

# Next Steps

Potential improvements:

* Add UC Davis resource data for retrieval
* Integrate an LLM or Hugging Face model
* Implement smarter query routing
* Replace `localStorage` with a persistent database
* Add authentication and user accounts

---

# Design

The interface preserves the original color palette:

* Background gradient: `#200E57 → #3B1FA6`
* Message and input containers: `#2A176B`
* Branding accent: `#FFD700`
* White borders and typography
