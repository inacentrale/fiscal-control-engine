import DashboardShell from "@/components/layout/DashboardShell";
import RasAuditReportPreviewPage from "@/components/reports/RasAuditReportPreviewPage";

export default async function RasAuditReportPage({
  params,
  searchParams,
}: {
  params: Promise<{ auditId: string }>;
  searchParams: Promise<{ session_id?: string; file_id?: string }>;
}) {
  const { auditId } = await params;
  const { session_id: sessionId = "", file_id: fileId = "" } =
    await searchParams;

  return (
    <DashboardShell>
      <RasAuditReportPreviewPage
        auditId={auditId}
        fileId={fileId}
        sessionId={sessionId}
      />
    </DashboardShell>
  );
}
