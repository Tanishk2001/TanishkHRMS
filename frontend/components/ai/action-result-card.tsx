const STATUS_STYLES: Record<string, string> = {
  SUCCESS: "border-good/30 bg-good/10 text-good",
  DENIED: "border-bad/30 bg-bad/10 text-bad",
  ERROR: "border-warn/30 bg-warn/10 text-warn",
  NEEDS_CONFIRMATION: "border-accent/30 bg-accent/10 text-ink",
};

interface Props {
  answer: string;
  status: string;
  needsConfirmation: boolean;
  onConfirm?: () => void;
  onCancel?: () => void;
}

export default function ActionResultCard({ answer, status, needsConfirmation, onConfirm, onCancel }: Props) {
  const style = STATUS_STYLES[status] ?? "border-border bg-surface-hi text-ink";

  return (
    <div className={`mt-2 border rounded-lg p-3 text-sm ${style}`}>
      <p>{answer}</p>
      {needsConfirmation && (
        <div className="mt-3 flex gap-2">
          <button
            onClick={onConfirm}
            className="px-3 py-1.5 rounded-md bg-accent text-white text-xs font-medium hover:bg-accent/90 transition-colors"
          >
            Confirm
          </button>
          <button
            onClick={onCancel}
            className="px-3 py-1.5 rounded-md border border-border text-xs font-medium hover:bg-surface-hi transition-colors"
          >
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}
