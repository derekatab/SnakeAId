'use client';

import { useState, useRef, useEffect } from 'react';
import Image from 'next/image';
import dynamic from 'next/dynamic';

interface Message {
    type: 'user' | 'bot';
    content: string;
    timestamp?: Date;
}

const initialMessage: Message = {
    type: 'bot',
    content: 'Hello! I\'m here to help with snake bite emergencies. Please describe the situation.',
    timestamp: new Date()
};

// Create a client-side only component
const ChatComponent = () => {
    const [messages, setMessages] = useState<Message[]>([initialMessage]);
    const [input, setInput] = useState('');
    const [isTyping, setIsTyping] = useState(false);
    const [hasReceivedFirstMessage, setHasReceivedFirstMessage] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        // Scroll to bottom when new messages arrive
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const resetChat = async () => {
        setIsTyping(true);
        setHasReceivedFirstMessage(false);
        setMessages([{ ...initialMessage, timestamp: new Date() }]);

        try {
            await fetch('http://localhost:5000/reset', {
                method: 'POST',
            });
        } catch (error) {
            console.error('Error resetting chat:', error);
        } finally {
            setIsTyping(false);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim()) return;

        // Add user message
        const userMessage = { type: 'user', content: input, timestamp: new Date() } as Message;
        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setIsTyping(true);

        try {
            const response = await fetch('http://localhost:5000/sms', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    Body: input,
                    From: 'web-user',
                    is_first_message: !hasReceivedFirstMessage
                })
            });

            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const data = await response.text();
            const botResponse = data.includes('<Message>')
                ? data.split('<Message>')[1].split('</Message>')[0]
                : data;

            setMessages(prev => [...prev, { type: 'bot', content: botResponse, timestamp: new Date() }]);
            setHasReceivedFirstMessage(true);
        } catch (error) {
            console.error('Error:', error);
            setMessages(prev => [...prev, {
                type: 'bot',
                content: hasReceivedFirstMessage
                    ? "I'm having trouble connecting right now. Please try again in a moment."
                    : `Move them away from the snake. Remove any tight items like rings or bracelets. Keep them calm and still.
Keep their leg still and straight. Don't tie anything around it or try to cut or suck the bite.
If transport is far, make a stretcher using a tarp, rope, or jackets. Get them to a health facility ASAP.
If they feel dizzy or vomit, lay them on their left side. Watch their breathing and be ready to help if needed.`,
                timestamp: new Date()
            }]);
        } finally {
            setIsTyping(false);
        }
    };

    const formatTime = (date: Date) => {
        return date.toLocaleTimeString('en-US', {
            hour: 'numeric',
            minute: '2-digit',
            hour12: true
        });
    };

    return (
        <main className="flex min-h-screen flex-col items-center bg-gradient-to-br from-green-50 via-emerald-50 to-teal-50 p-4 sm:p-6 md:p-8">
            <div className="w-full max-w-4xl bg-white rounded-2xl shadow-2xl overflow-hidden border border-gray-100">
                {/* Header */}
                <div className="bg-gradient-to-r from-green-600 via-green-500 to-emerald-600 p-8 text-white relative overflow-hidden">
                    <div className="absolute inset-0 bg-[url('/snake-pattern.png')] opacity-10"></div>
                    <div className="relative z-10">
                        <div className="flex items-center justify-center mb-4">
                            <div className="relative">
                                <div className="absolute -inset-1 bg-white/20 rounded-full blur"></div>
                                <Image
                                    src="/logo.svg"
                                    alt="SnakeAid Logo"
                                    width={56}
                                    height={56}
                                    className="relative"
                                />
                            </div>
                            <h1 className="text-4xl font-bold tracking-tight ml-4 text-shadow">SnakeAid</h1>
                        </div>
                        <p className="text-lg text-center text-green-50 max-w-2xl mx-auto">
                            Your SMS/WhatsApp emergency guide in the event of a snake bite
                        </p>
                        <div className="flex justify-center mt-4">
                            <span className="inline-flex items-center px-4 py-2 rounded-full bg-green-700/30 text-sm">
                                <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse mr-2"></span>
                                Available 24/7 for Emergency Assistance
                            </span>
                        </div>
                    </div>
                </div>

                {/* Chat Messages */}
                <div className="h-[500px] overflow-y-auto p-6 space-y-4 bg-gradient-to-b from-gray-50 to-white">
                    {messages.map((message, index) => (
                        <div
                            key={index}
                            className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'} animate-fadeIn`}
                        >
                            <div
                                className={`max-w-[85%] rounded-2xl p-4 shadow-sm transition-all duration-200 hover:shadow-md ${message.type === 'user'
                                    ? 'bg-gradient-to-br from-green-600 to-emerald-600 text-white'
                                    : 'bg-white text-gray-800 border border-gray-100'
                                    }`}
                            >
                                <pre className="whitespace-pre-wrap font-sans text-sm md:text-base leading-relaxed">{message.content}</pre>
                                {message.timestamp && (
                                    <div className={`text-xs mt-2 ${message.type === 'user' ? 'text-green-100' : 'text-gray-400'}`}>
                                        {formatTime(message.timestamp)}
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                    {isTyping && (
                        <div className="flex items-center space-x-2 text-gray-400 text-sm">
                            <div className="flex space-x-1">
                                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                            </div>
                            <span>SnakeAid is typing...</span>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                {/* Input Form and Reset Button */}
                <div className="p-6 border-t border-gray-100 bg-white">
                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div className="flex space-x-3">
                            <input
                                type="text"
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                placeholder="Describe the emergency..."
                                className="flex-1 p-4 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent text-gray-800 transition-shadow duration-200 hover:shadow-sm"
                            />
                            <button
                                type="submit"
                                className="bg-gradient-to-r from-green-600 to-emerald-600 text-white px-8 py-4 rounded-xl hover:shadow-lg transition-all duration-200 font-medium shadow-sm hover:translate-y-[-1px] active:translate-y-[1px]"
                                disabled={isTyping}
                            >
                                Send
                            </button>
                        </div>
                        <div className="flex items-center justify-between">
                            <button
                                type="button"
                                onClick={resetChat}
                                className="text-gray-500 hover:text-gray-700 text-sm py-2 transition-colors duration-200 flex items-center"
                                disabled={isTyping}
                            >
                                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                </svg>
                                Reset Conversation
                            </button>
                            <span className="text-xs text-gray-400">
                                Emergency? Call your local emergency services immediately
                            </span>
                        </div>
                    </form>
                </div>
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