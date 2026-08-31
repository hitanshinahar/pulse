import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

interface RouteContext {
    params: Promise<{
        decisionId: string;
    }>;
}

export async function POST(
    request: NextRequest,
    { params }: RouteContext
) {
    try {
        const { decisionId } = await params;

        const body = await request.text();

        const response = await fetch(
            `${BACKEND_URL}/api/v1/recovery/decisions/${decisionId}/evaluate`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: body || undefined,
            }
        );

        const data = await response.json();

        return NextResponse.json(data, {
            status: response.status,
        });
    } catch (error) {
        console.error("Recovery firewall proxy error:", error);

        return NextResponse.json(
            {
                detail: "Unable to reach recovery backend",
            },
            {
                status: 502,
            }
        );
    }
}