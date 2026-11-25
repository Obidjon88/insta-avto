import React from "react";
import { CalculateMetadataFunction, Composition } from "remotion";
import { QuoteReel, QuoteProps, quoteSchema, totalSeconds } from "./QuoteReel";

const calculateMetadata: CalculateMetadataFunction<QuoteProps> = ({ props }) => {
  return { durationInFrames: Math.round(totalSeconds(props.lines) * 30) };
};

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="QuoteReel"
      component={QuoteReel}
      schema={quoteSchema}
      durationInFrames={300}
      fps={30}
      width={1080}
      height={1920}
      calculateMetadata={calculateMetadata}
      defaultProps={{
        lines: ["Время не лечит.", "Оно учит жить", "с тем, что болит.", "И в этом тоже сила."],
        topLabel: "Как-то так...",
        theme: "rain",
        handle: "@obidjon_gafarov",
        cta: "Сохрани, чтобы не забыть 🔖",
        music: "",
        seed: 7,
      }}
    />
  );
};
