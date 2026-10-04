import { Composition } from "remotion";
import { Reel, TOTAL } from "./Reel";
export const Root = () => (
  <Composition id="ComplaintIQReel" component={Reel} durationInFrames={TOTAL} fps={30} width={1920} height={1080} />
);
