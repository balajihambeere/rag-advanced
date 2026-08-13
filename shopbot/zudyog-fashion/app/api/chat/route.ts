import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.SHOPBOT_API_URL ?? "http://localhost:8000";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();

    const res = await fetch(`${BACKEND_URL}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const text = await res.text();
      return NextResponse.json(
        { answer: `Backend error (${res.status}): ${text}` },
        { status: res.status }
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json(
      {
        answer:
          "The ShopBot API is not reachable. Make sure the Python backend is running on port 8000.",
        error: message,
      },
      { status: 503 }
    );
  }
}
