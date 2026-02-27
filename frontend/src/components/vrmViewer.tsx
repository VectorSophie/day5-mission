import { useContext, useCallback } from "react";
import { ViewerContext } from "../features/vrmViewer/viewerContext";
import { getApiBase } from "@/utils/apiBase";

export default function VrmViewer() {
  const { viewer } = useContext(ViewerContext);
  const LOCAL_LUMI_VRM_URL = `${getApiBase()}/model/lumi.vrm`;

  const canvasRef = useCallback(
    (canvas: HTMLCanvasElement) => {
      if (canvas) {
        viewer.setup(canvas);
        viewer.loadVrm(LOCAL_LUMI_VRM_URL);

        // Drag and DropでVRMを差し替え
        canvas.addEventListener("dragover", function (event) {
          event.preventDefault();
        });

        canvas.addEventListener("drop", function (event) {
          event.preventDefault();

          const files = event.dataTransfer?.files;
          if (!files) {
            return;
          }

          const file = files[0];
          if (!file) {
            return;
          }

          const file_type = file.name.split(".").pop();
          if (file_type === "vrm") {
            const blob = new Blob([file], { type: "application/octet-stream" });
            const url = window.URL.createObjectURL(blob);
            viewer.loadVrm(url);
          }
        });
      }
    },
    [viewer, LOCAL_LUMI_VRM_URL]
  );

  return (
    <div className={"absolute top-0 left-0 w-screen h-[100svh] -z-10"}>
      <canvas ref={canvasRef} className={"h-full w-full"}></canvas>
    </div>
  );
}
