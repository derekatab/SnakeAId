'use client';

import { useState, useRef, useEffect } from 'react';
import Image from 'next/image';
import dynamic from 'next/dynamic';

interface Message {
  type: 'user' | 'bot';
  content: string;
}

const initialMessage: Message = {
  type: 'bot',
  content: 'Hello! I\'m here to help with snake bite emergencies. Please describe the situation.'
};

// Create a client-side only component
const ChatComponent = () => {
  const [messages, setMessages] = useState<Message[]>([initialMessage]);
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Scroll to bottom when new messages arrive
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    // Add user message
    const userMessage = { type: 'user', content: input } as Message;
    setMessages(prev => [...prev, userMessage]);
    setInput('');

    try {
      // Send message through Twilio
      const response = await fetch('http://localhost:5000/sms', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          Body: input,
          From: 'web-user'
        })
      });

      if (!response.ok) {
        throw new Error('Network response was not ok');
      }

      const data = await response.text();
      // Extract message from Twilio's XML response
      const botResponse = data.includes('<Message>') 
        ? data.split('<Message>')[1].split('</Message>')[0]
        : data;

      setMessages(prev => [...prev, { type: 'bot', content: botResponse }]);
    } catch (error) {
      console.error('Error:', error);
      setMessages(prev => [...prev, {
        type: 'bot',
        content: "Immediately move away from the area where the bite occurred.\n\n If the snake is still attached use a stick or tool to make it let go.\n\n Seek medical support immediately: the emergency number in this area is 999."
      }]);
    }
  };

  return (
    <main className="flex min-h-screen flex-col items-center bg-gray-100 p-4">
      <div className="w-full max-w-2xl bg-white rounded-lg shadow-xl overflow-hidden">
        {/* Header */}
        <div className="bg-green-600 p-4 text-white">
          <div className="flex items-center justify-center mb-2">
            <Image
              src="/logo.svg"
              alt="SnakeAid Logo"
              width={40}
              height={40}
              className="mr-2"
            />
            <h1 className="text-2xl font-bold">SnakeAid</h1>
          </div>
          <p className="text-sm opacity-90 text-center">Your SMS/WhatsApp emergency guide</p>
        </div>

        {/* Chat Messages */}
        <div className="h-[600px] overflow-y-auto p-4 space-y-4">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] rounded-lg p-3 ${
                  message.type === 'user'
                    ? 'bg-green-500 text-white'
                    : 'bg-gray-100 text-gray-800'
                }`}
              >
                <pre className="whitespace-pre-wrap font-sans">{message.content}</pre>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Form */}
        <form onSubmit={handleSubmit} className="p-4 border-t border-gray-200">
          <div className="flex space-x-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Describe the emergency..."
              className="flex-1 p-2 border border-gray-300 rounded-lg focus:outline-none focus:border-green-500"
            />
            <button
              type="submit"
              className="bg-green-500 text-white px-4 py-2 rounded-lg hover:bg-green-600 transition-colors"
            >
              Send
            </button>
          </div>
        </form>
      </div>
    </main>
  );
};

// Use dynamic import with ssr disabled for the chat component
const Chat = dynamic(() => Promise.resolve(ChatComponent), {
  ssr: false,
});

// Main page component
export default function Home() {
  return <Chat />;
}
