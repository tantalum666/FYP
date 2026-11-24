import { useLayoutEffect, useRef, type ReactNode, type RefObject } from "react";

export function ConversationScroll({
  children,
  followLatest,
}: {
  children: ReactNode;
  followLatest: RefObject<boolean>;
}) {
  const viewport = useRef<HTMLDivElement>(null);
  const content = useRef<HTMLDivElement>(null);
  const lastScrollTop = useRef(0);

  useLayoutEffect(() => {
    const node = viewport.current;
    if (!node || !content.current) return;
    const follow = () => {
      if (!followLatest.current || !node.clientHeight) return;
      node.scrollTo({ top: node.scrollHeight, behavior: "instant" });
      lastScrollTop.current = node.scrollTop;
    };
    // Captions, job details and fonts can resize after a React commit.
    const observer = new ResizeObserver(follow);
    observer.observe(node);
    observer.observe(content.current);
    follow();
    return () => observer.disconnect();
  }, [followLatest]);

  return (
    <div
      className="assistant-conversation"
      ref={viewport}
      onScroll={({ currentTarget: node }) => {
        if (!node.clientHeight) return;
        if (node.scrollHeight - node.scrollTop - node.clientHeight <= 2)
          followLatest.current = true;
        else if (node.scrollTop < lastScrollTop.current)
          followLatest.current = false;
        lastScrollTop.current = node.scrollTop;
      }}
    >
      <div className="assistant-transcript-content" ref={content}>
        {children}
      </div>
    </div>
  );
}
