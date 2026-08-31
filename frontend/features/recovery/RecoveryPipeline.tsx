interface RecoveryPipelineProps {
    currentStage?: number;
}

const stages = [
    "Candidate",
    "Prediction",
    "Decision",
    "Firewall",
    "Execution",
];

export function RecoveryPipeline({
    currentStage = 1,
}: RecoveryPipelineProps) {
    return (
        <div className="recovery-pipeline">
            {stages.map((stage, index) => {
                const stageNumber = index + 1;
                const isActive = stageNumber <= currentStage;

                return (
                    <div className="recovery-pipeline__item" key={stage}>
                        <div
                            className={`recovery-pipeline__node ${isActive ? "recovery-pipeline__node--active" : ""
                                }`}
                        >
                            <span>{String(stageNumber).padStart(2, "0")}</span>
                        </div>

                        <span className="recovery-pipeline__label">
                            {stage}
                        </span>

                        {index < stages.length - 1 && (
                            <div
                                className={`recovery-pipeline__connector ${stageNumber < currentStage
                                        ? "recovery-pipeline__connector--active"
                                        : ""
                                    }`}
                            />
                        )}
                    </div>
                );
            })}
        </div>
    );
}