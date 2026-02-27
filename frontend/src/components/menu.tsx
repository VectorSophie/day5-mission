import { IconButton } from "./iconButton";
import { Message } from "@/features/messages/messages";
import { ChatLog } from "./chatLog";
import { AssistantText } from "./assistantText";
import { useState } from "react";

type Props = {
  chatLog: Message[];
  assistantMessage: string;
};

export const Menu = ({ chatLog, assistantMessage }: Props) => {
  const [showChatLog, setShowChatLog] = useState(false);

  return (
    <>
      <div className="absolute z-10 m-24">
        <div className="grid grid-flow-col gap-[8px]">
          {showChatLog ? (
            <IconButton
              iconName="24/CommentOutline"
              label="Conversation Log"
              isProcessing={false}
              onClick={() => setShowChatLog(false)}
            />
          ) : (
            <IconButton
              iconName="24/CommentFill"
              label="Conversation Log"
              isProcessing={false}
              disabled={chatLog.length <= 0}
              onClick={() => setShowChatLog(true)}
            />
          )}
        </div>
      </div>
      {showChatLog && <ChatLog messages={chatLog} />}
      {!showChatLog && assistantMessage && <AssistantText message={assistantMessage} />}
    </>
  );
};
