import { NextResponse } from "next/server";

const BACKEND_URL =
    process.env.BACKEND_URL ||
    "http://localhost:8000";

export async function POST(
    _request: Request,
    {
        params,
    }: {
        params: Promise<{ executionId: string }>;
    }
) {
    try {
        const { executionId } = await params;

        const response = await fetch(
            `${BACKEND_URL}/api/v1/recovery/executions/${executionId}/execute`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
            }
        );

        const data = await response.json();

        return NextResponse.json(data, {
            status: response.status,
        });
    } catch {
        return NextResponse.json(
            {
                detail: "Unable to reach recovery backend.",
            },
            { status: 502 }
        );
    }
}