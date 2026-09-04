import { NextResponse } from "next/server";

const BACKEND_URL =
    process.env.BACKEND_URL ||
    "http://localhost:8000";

export async function GET(
    _request: Request,
    {
        params,
    }: {
        params: Promise<{ decisionId: string }>;
    }
) {
    try {
        const { decisionId } = await params;

        const response = await fetch(
            `${BACKEND_URL}/api/v1/recovery/decisions/${decisionId}/audit`,
            {
                method: "GET",
                cache: "no-store",
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