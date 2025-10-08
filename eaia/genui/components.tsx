import { useStreamContext } from "@langchain/langgraph-sdk/react-ui";
import React from "react";
import "../../styles.css";

const openInGmailButton = (emailId: string, compact: boolean = false) => (
  <a
    href={`https://mail.google.com/mail/u/0/#inbox/${emailId}`}
    target="_blank"
    className={compact
      ? "inline-flex items-center gap-1.5 rounded-md bg-white px-3 py-1.5 text-sm font-medium text-gray-700 border border-gray-300 hover:bg-gray-50 transition-colors"
      : "inline-flex items-center gap-2 rounded-md bg-white px-4 py-2 text-sm font-medium text-gray-700 border border-gray-300 hover:bg-gray-50 transition-colors"
    }
  >
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M22 6C22 4.9 21.1 4 20 4H4C2.9 4 2 4.9 2 6V18C2 19.1 2.9 20 4 20H20C21.1 20 22 19.1 22 18V6ZM20 6L12 11L4 6H20ZM20 18H4V8L12 13L20 8V18Z" fill="#EA4335"/>
    </svg>
    Open in Gmail
  </a>
);

const EmailMarkedAsReadComponent = () => {
    const { values, meta } = useStreamContext<
      {},
      { MetaType: {
        args?: Record<string, any>,
        result?: string,
        status?: "pending" | "completed" | "error" | "interrupted"
      }}
    >();
    const result = meta?.result;
    const status = meta?.status || "pending";

    const getBorderColor = () => {
      if (status === "error" || status === "interrupted") return "border-red-500";
      return "border-gray-200";
    };

    const getContent = () => {
      if (status === "pending") {
        return (
          <div className="flex items-center gap-2 text-gray-600">
            <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Marking email as read...
          </div>
        );
      }

      if (status === "error") {
        return <div className="text-red-600">{result || "An error occurred"}</div>;
      }

      if (status === "interrupted") {
        return <div className="text-red-600">Error: Process was interrupted</div>;
      }

      return <div className="text-gray-700">{result || "Email marked as read"}</div>;
    };

    return (
      <div className={`rounded-lg border-2 ${getBorderColor()} p-4 bg-white w-full max-w-full`}>
        <div className="flex flex-col gap-3">
          {getContent()}
          {openInGmailButton(values.email?.id || "", "Open in Gmail")}
        </div>
      </div>
    );
}

const WriteEmailResponseComponent = () => {
    const { values, meta, submit } = useStreamContext<
      { email?: { id?: string } },
      { MetaType: {
        args?: Record<string, any>,
        result?: string,
        status?: "pending" | "completed" | "error" | "interrupted"
      }}
    >();
    const args = meta?.args || {};
    const status = meta?.status || "pending";

    // Handle recipients - could be array or string
    const getRecipientsArray = (recipients: any): string[] => {
      if (!recipients) return [];
      if (Array.isArray(recipients)) return recipients;
      if (typeof recipients === 'string') {
        try {
          return JSON.parse(recipients);
        } catch {
          return [recipients];
        }
      }
      return [];
    };

    const [recipients, setRecipients] = React.useState<string[]>(getRecipientsArray(args.new_recipients));
    const [content, setContent] = React.useState<string>(args.content || "");
    const [feedback, setFeedback] = React.useState<string>("");

    // Update internal state when args change
    React.useEffect(() => {
      if (args.new_recipients) setRecipients(getRecipientsArray(args.new_recipients));
      if (args.content) setContent(args.content);
    }, [args.new_recipients, args.content]);

    const copyToClipboard = (text: string) => {
      navigator.clipboard.writeText(text);
    };

    const handleSendEmail = () => {
      if (recipients == args.new_recipients && content == args.content) {
        submit(null, { command: { resume: [
          {
            type: "accept",
            args: null
          }
        ] } })
      } else {
        submit(null, { command: { resume: [
          {
            type: "edit",
            args: {
              action: "write_email_response",
              args: {
                new_recipients: recipients,
                content
              }
            }
          }
        ] } })
      }
    };

    const handleSubmitFeedback = () => {
      const feedbackMessage = `User Feedback: ${feedback}`;
      submit(null, { command: { resume: [
        {
          type: "response",
          args: feedbackMessage
        }
      ] } })
    };

    const getBorderColor = () => {
      if (status === "error") return "border-red-500";
      if (status === "interrupted") return "border-purple-500";
      if (status === "completed") {
        const result = meta?.result;
        const isCancelled = result && typeof result === 'string' && result.includes("Please ignore this tool call, it did not execute.");
        const hasFeedback = result && typeof result === 'string' && result.includes("User Feedback:");
        if (isCancelled) return "border-yellow-500";
        if (hasFeedback) return "border-purple-500";
        return "border-green-500";
      }
      return "border-blue-500";
    };

    const getStatusBanner = () => {
      const result = meta?.result;
      const isCancelled = result && typeof result === 'string' && result.includes("Please ignore this tool call, it did not execute.");
      const hasFeedback = result && typeof result === 'string' && result.includes("User Feedback:");

      if (status === "pending") {
        return (
          <div className="flex items-center gap-2 text-blue-600 mb-4 p-3 bg-blue-50 rounded-md">
            <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Sending Email Response...
          </div>
        );
      }

      if (status === "completed") {
        if (isCancelled) {
          return (
            <div className="flex items-center gap-2 text-yellow-600 mb-4 p-3 bg-yellow-50 rounded-md">
              <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              Tool Call Cancelled
            </div>
          );
        }
        if (hasFeedback) {
          return (
            <div className="flex flex-col gap-2 text-purple-600 mb-4 p-3 bg-purple-50 rounded-md">
              <div className="flex items-center gap-2 font-medium">
                <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
                </svg>
                Feedback provided:
              </div>
              <div className="text-sm pl-7">{result}</div>
            </div>
          );
        }
        return (
          <div className="flex items-center gap-2 text-green-600 mb-4 p-3 bg-green-50 rounded-md">
            <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            Email Successfully Sent
          </div>
        );
      }

      if (status === "error") {
        return (
          <div className="flex items-center gap-2 text-red-600 mb-4 p-3 bg-red-50 rounded-md">
            <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
            Could not send email
          </div>
        );
      }

      return null;
    };

    const isEditable = status === "interrupted";

    return (
      <div className={`rounded-lg border-2 ${getBorderColor()} p-4 bg-white w-full max-w-full`}>
        {status === "interrupted" && (
          <div className="flex items-center gap-2 text-purple-600 mb-4 p-3 bg-purple-50 rounded-md font-medium">
            <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Awaiting user input...
          </div>
        )}
        {getStatusBanner()}

        <div className="flex flex-col gap-4 w-full">
          {/* Recipients Section */}
          <div className="relative">
            <div className="flex justify-between items-center mb-2">
              <label className="text-sm font-medium text-gray-700">Additional Recipients (optional):</label>
              <button
                onClick={() => copyToClipboard(recipients.join(", "))}
                className="opacity-0 hover:opacity-100 transition-opacity p-1 hover:bg-gray-100 rounded"
                title="Copy recipients"
              >
                <svg className="h-4 w-4 text-gray-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </button>
            </div>
            {isEditable ? (
              <input
                type="text"
                value={recipients.join(", ")}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setRecipients(e.target.value.split(",").map((r: string) => r.trim()))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="recipient@example.com"
              />
            ) : (
              <div className="px-3 py-2 bg-gray-50 rounded-md text-gray-700 border border-gray-200">
                {recipients.join(", ")}
              </div>
            )}
          </div>

          {/* Content Section */}
          <div className="relative">
            <div className="flex justify-between items-center mb-2">
              <label className="text-sm font-medium text-gray-700">Message:</label>
              <button
                onClick={() => copyToClipboard(content)}
                className="opacity-0 hover:opacity-100 transition-opacity p-1 hover:bg-gray-100 rounded"
                title="Copy content"
              >
                <svg className="h-4 w-4 text-gray-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </button>
            </div>
            {isEditable ? (
              <textarea
                value={content}
                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setContent(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[400px] font-mono text-sm"
                placeholder="Email content..."
              />
            ) : (
              <div className="px-3 py-2 bg-gray-50 rounded-md text-gray-700 border border-gray-200 min-h-[400px] whitespace-pre-wrap font-mono text-sm">
                {content}
              </div>
            )}
          </div>

          {/* Send Button - Only shown in interrupted state */}
          {isEditable && (
            <div className="flex gap-2 self-end">
              {openInGmailButton(values.email?.id || "", true)}
              <button
                onClick={handleSendEmail}
                className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors font-medium"
              >
                Send Email
              </button>
            </div>
          )}

          {/* Feedback Section - Only shown in interrupted state */}
          {isEditable && (
            <div className="mt-6 pt-6 border-t-2 border-gray-200">
              <div className="flex flex-col gap-3">
                <label className="text-sm font-medium text-gray-600 italic">
                  Ask your assistant to edit this draft, or take a different action
                </label>
                <div className="flex gap-2">
                  <textarea
                    value={feedback}
                    onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setFeedback(e.target.value)}
                    onKeyDown={(e: React.KeyboardEvent<HTMLTextAreaElement>) => {
                      if ((e.metaKey || e.ctrlKey) && e.key === "Enter" && feedback.trim()) {
                        e.preventDefault();
                        handleSubmitFeedback();
                      }
                    }}
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 min-h-[80px] bg-purple-50/30"
                    placeholder="e.g., 'Make the tone more formal' or 'Add a closing paragraph'"
                  />
                </div>
                <button
                  onClick={handleSubmitFeedback}
                  disabled={!feedback.trim()}
                  className="self-end px-3 py-1.5 text-sm bg-purple-600 text-white rounded-md hover:bg-purple-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-purple-600"
                >
                  Submit Feedback
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    );
}

const MessageUserComponent = () => {
    const { values, meta, submit } = useStreamContext<
      { email?: { id?: string } },
      { MetaType: {
        args?: Record<string, any>,
        result?: string,
        status?: "pending" | "completed" | "error" | "interrupted"
      }}
    >();
    const args = meta?.args || {};
    const status = meta?.status || "pending";
    const result = meta?.result;

    const [response, setResponse] = React.useState<string>("");

    const handleSubmitResponse = () => {
      submit(null, { command: { resume: [
          {
            type: "response",
            args: response         
          }
        ] } })
    };

    // Pending state - return empty component
    if (status === "pending") {
      return null;
    }

    // Error state
    if (status === "error") {
      return (
        <div className="rounded-lg border-2 border-red-500 p-4 bg-white w-full max-w-full">
          <div className="flex items-center gap-2 text-red-600 p-3 bg-red-50 rounded-md">
            <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
            {result || "An error occurred"}
          </div>
        </div>
      );
    }

    // Completed state
    if (status === "completed") {
      const isCancelled = result && typeof result === 'string' && result.includes("Please ignore this tool call, it did not execute.");

      if (isCancelled) {
        return (
          <div className="rounded-lg border-2 border-yellow-500 p-4 bg-white w-full max-w-full">
            <div className="flex items-center gap-2 text-yellow-600 p-3 bg-yellow-50 rounded-md">
              <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              Tool Call Cancelled
            </div>
          </div>
        );
      }

      return (
        <div className="rounded-lg border-2 border-green-500 p-4 bg-white w-full max-w-full">
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-2 text-green-600 font-medium">
              <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Response received
            </div>
            <div className="px-3 py-2 bg-gray-50 rounded-md text-gray-700 border border-gray-200 whitespace-pre-wrap">
              {result}
            </div>
          </div>
        </div>
      );
    }

    // Interrupted state
    const question = args.question_for_user || "";

    return (
      <div className="rounded-lg border-2 border-purple-500 p-4 bg-white w-full max-w-full">
        <div className="flex items-center gap-2 text-purple-600 mb-4 p-3 bg-purple-50 rounded-md font-medium">
          <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Awaiting user input...
        </div>
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-2 text-blue-600 font-medium">
            <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Question
          </div>

          <div className="px-3 py-2 bg-blue-50 rounded-md text-gray-700 border border-blue-200">
            {question}
          </div>

          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-gray-700">Your Response:</label>
            <textarea
              value={response}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setResponse(e.target.value)}
              onKeyDown={(e: React.KeyboardEvent<HTMLTextAreaElement>) => {
                if ((e.metaKey || e.ctrlKey) && e.key === "Enter" && response.trim()) {
                  e.preventDefault();
                  handleSubmitResponse();
                }
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[100px]"
              placeholder="Type your response here..."
            />
          </div>

          <div className="flex gap-2 self-end">
            {openInGmailButton(values.email?.id || "", true)}
            <button
              onClick={handleSubmitResponse}
              disabled={!response.trim()}
              className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-blue-600"
            >
              Submit Response
            </button>
          </div>
        </div>
      </div>
    );
}

const SendCalendarInviteComponent = () => {
    const { meta, submit } = useStreamContext<
      {},
      { MetaType: {
        args?: Record<string, any>,
        result?: string,
        status?: "pending" | "completed" | "error" | "interrupted"
      }}
    >();
    const args = meta?.args || {};
    const status = meta?.status || "pending";
    const result = meta?.result;

    const [emails, setEmails] = React.useState<string[]>(args.emails || []);
    const [eventTitle, setEventTitle] = React.useState<string>(args.event_title || "");
    const [startTime, setStartTime] = React.useState<string>(args.start_time || "");
    const [endTime, setEndTime] = React.useState<string>(args.end_time || "");
    const [timezone, setTimezone] = React.useState<string>(args.timezone || "America/New_York");
    const [feedback, setFeedback] = React.useState<string>("");

    const handleScheduleEvent = () => {
      submit(null, { command: { resume: [
        {
          type: "edit",
          args: {
            action: "send_calendar_invite",
            args: {
              emails,
              event_title: eventTitle,
              start_time: startTime,
              end_time: endTime,
              timezone
            }
          }
        }
      ] } })
    };

    const handleSubmitFeedback = () => {
      const feedbackMessage = `User Feedback: ${feedback}`;
      console.log("Submitting feedback:", feedbackMessage);
      submit(null, { command: { resume: [
        {
          type: "response",
          args: feedbackMessage
        }
      ] } })
    };

    const getBorderColor = () => {
      if (status === "error") return "border-red-500";
      if (status === "interrupted") return "border-purple-500";
      if (status === "completed") {
        const isCancelled = result && typeof result === 'string' && result.includes("Please ignore this tool call, it did not execute.");
        const hasFeedback = result && typeof result === 'string' && result.includes("User Feedback:");
        if (isCancelled) return "border-yellow-500";
        if (hasFeedback) return "border-purple-500";
        return "border-green-500";
      }
      return "border-blue-500";
    };

    const getStatusBanner = () => {
      const isCancelled = result && typeof result === 'string' && result.includes("Please ignore this tool call, it did not execute.");
      const hasFeedback = result && typeof result === 'string' && result.includes("User Feedback:");

      if (status === "pending") {
        return (
          <div className="flex items-center gap-2 text-blue-600 mb-4 p-3 bg-blue-50 rounded-md">
            <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Scheduling event...
          </div>
        );
      }

      if (status === "completed") {
        if (isCancelled) {
          return (
            <div className="flex items-center gap-2 text-yellow-600 mb-4 p-3 bg-yellow-50 rounded-md">
              <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              Tool Call Cancelled
            </div>
          );
        }
        if (hasFeedback) {
          return (
            <div className="flex flex-col gap-2 text-purple-600 mb-4 p-3 bg-purple-50 rounded-md">
              <div className="flex items-center gap-2 font-medium">
                <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
                </svg>
                Feedback provided:
              </div>
              <div className="text-sm pl-7">{result}</div>
            </div>
          );
        }
        return (
          <div className="flex items-center gap-2 text-green-600 mb-4 p-3 bg-green-50 rounded-md">
            <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            Successfully scheduled
          </div>
        );
      }

      if (status === "error") {
        return (
          <div className="flex items-center gap-2 text-red-600 mb-4 p-3 bg-red-50 rounded-md">
            <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
            {result || "Failed to schedule event"}
          </div>
        );
      }

      return null;
    };

    const isEditable = status === "interrupted";

    return (
      <div className={`rounded-lg border-2 ${getBorderColor()} p-4 bg-white w-full max-w-full`}>
        {status === "interrupted" && (
          <div className="flex items-center gap-2 text-purple-600 mb-4 p-3 bg-purple-50 rounded-md font-medium">
            <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Awaiting user input...
          </div>
        )}
        {getStatusBanner()}

        <div className="flex flex-col gap-4 w-full">
          {/* Event Title */}
          <div>
            <label className="text-sm font-medium text-gray-700 mb-2 block">Event Title:</label>
            {isEditable ? (
              <input
                type="text"
                value={eventTitle}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEventTitle(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Event title"
              />
            ) : (
              <div className="px-3 py-2 bg-gray-50 rounded-md text-gray-700 border border-gray-200 font-medium">
                {eventTitle}
              </div>
            )}
          </div>

          {/* Attendees */}
          <div>
            <label className="text-sm font-medium text-gray-700 mb-2 block">Attendees:</label>
            {isEditable ? (
              <input
                type="text"
                value={emails.join(", ")}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEmails(e.target.value.split(",").map((email: string) => email.trim()))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="email@example.com, another@example.com"
              />
            ) : (
              <div className="px-3 py-2 bg-gray-50 rounded-md text-gray-700 border border-gray-200">
                {emails.join(", ")}
              </div>
            )}
          </div>

          {/* Start Time */}
          <div>
            <label className="text-sm font-medium text-gray-700 mb-2 block">Start Time:</label>
            {isEditable ? (
              <input
                type="datetime-local"
                value={startTime}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setStartTime(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            ) : (
              <div className="px-3 py-2 bg-gray-50 rounded-md text-gray-700 border border-gray-200">
                {new Date(startTime).toLocaleString()}
              </div>
            )}
          </div>

          {/* End Time */}
          <div>
            <label className="text-sm font-medium text-gray-700 mb-2 block">End Time:</label>
            {isEditable ? (
              <input
                type="datetime-local"
                value={endTime}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEndTime(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            ) : (
              <div className="px-3 py-2 bg-gray-50 rounded-md text-gray-700 border border-gray-200">
                {new Date(endTime).toLocaleString()}
              </div>
            )}
          </div>

          {/* Timezone */}
          <div>
            <label className="text-sm font-medium text-gray-700 mb-2 block">Timezone:</label>
            {isEditable ? (
              <input
                type="text"
                value={timezone}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setTimezone(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="America/New_York"
              />
            ) : (
              <div className="px-3 py-2 bg-gray-50 rounded-md text-gray-700 border border-gray-200">
                {timezone}
              </div>
            )}
          </div>

          {/* Schedule Button - Only shown in interrupted state */}
          {isEditable && (
            <button
              onClick={handleScheduleEvent}
              className="self-end px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors font-medium"
            >
              Schedule Event
            </button>
          )}

          {/* Feedback Section - Only shown in interrupted state */}
          {isEditable && (
            <div className="mt-6 pt-6 border-t-2 border-gray-200">
              <div className="flex flex-col gap-3">
                <label className="text-sm font-medium text-gray-600 italic">
                  Ask your assistant to edit this event, or take a different action
                </label>
                <div className="flex gap-2">
                  <textarea
                    value={feedback}
                    onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setFeedback(e.target.value)}
                    onKeyDown={(e: React.KeyboardEvent<HTMLTextAreaElement>) => {
                      if ((e.metaKey || e.ctrlKey) && e.key === "Enter" && feedback.trim()) {
                        e.preventDefault();
                        handleSubmitFeedback();
                      }
                    }}
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 min-h-[80px] bg-purple-50/30"
                    placeholder="e.g., 'Change the time to 3pm' or 'Add more attendees'"
                  />
                </div>
                <button
                  onClick={handleSubmitFeedback}
                  disabled={!feedback.trim()}
                  className="self-end px-3 py-1.5 text-sm bg-purple-600 text-white rounded-md hover:bg-purple-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-purple-600"
                >
                  Submit Feedback
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    );
}

const StartNewEmailThreadComponent = () => {
    const { values, meta, submit } = useStreamContext<
      { email?: { id?: string } },
      { MetaType: {
        args?: Record<string, any>,
        result?: string,
        status?: "pending" | "completed" | "error" | "interrupted"
      }}
    >();
    const args = meta?.args || {};
    const status = meta?.status || "pending";

    // Handle recipients - could be array or string
    const getRecipientsArray = (recipients: any): string[] => {
      if (!recipients) return [];
      if (Array.isArray(recipients)) return recipients;
      if (typeof recipients === 'string') {
        try {
          return JSON.parse(recipients);
        } catch {
          return [recipients];
        }
      }
      return [];
    };

    const [recipients, setRecipients] = React.useState<string[]>(getRecipientsArray(args.recipients));
    const [subject, setSubject] = React.useState<string>(args.subject || "");
    const [content, setContent] = React.useState<string>(args.content || "");
    const [feedback, setFeedback] = React.useState<string>("");

    // Update internal state when args change
    React.useEffect(() => {
      if (args.recipients) setRecipients(getRecipientsArray(args.recipients));
      if (args.subject) setSubject(args.subject);
      if (args.content) setContent(args.content);
    }, [args.recipients, args.subject, args.content]);

    const copyToClipboard = (text: string) => {
      navigator.clipboard.writeText(text);
    };

    const handleSendEmail = () => {
      if (recipients == args.recipients && subject == args.subject && content == args.content) {
        submit(null, { command: { resume: [
          {
            type: "accept",
            args: null
          }
        ] } })
      } else {
        submit(null, { command: { resume: [
          {
            type: "edit",
            args: {
              action: "start_new_email_thread",
              args: {
                recipients,
                subject,
                content
              }
            }
          }
        ] } })
      }
    };

    const handleSubmitFeedback = () => {
      submit(null, { command: { resume: [
        {
          type: "response",
          args: `User Feedback: ${feedback}`
        }
      ] } })
    };

    const getBorderColor = () => {
      if (status === "error") return "border-red-500";
      if (status === "interrupted") return "border-purple-500";
      if (status === "completed") {
        const result = meta?.result;
        const isCancelled = result && typeof result === 'string' && result.includes("Please ignore this tool call, it did not execute.");
        const hasFeedback = result && typeof result === 'string' && result.includes("User Feedback:");
        if (isCancelled) return "border-yellow-500";
        if (hasFeedback) return "border-purple-500";
        return "border-green-500";
      }
      return "border-blue-500";
    };

    const getStatusBanner = () => {
      const result = meta?.result;
      const isCancelled = result && typeof result === 'string' && result.includes("Please ignore this tool call, it did not execute.");
      const hasFeedback = result && typeof result === 'string' && result.includes("User Feedback:");

      if (status === "pending") {
        return (
          <div className="flex items-center gap-2 text-blue-600 mb-4 p-3 bg-blue-50 rounded-md">
            <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Sending Email...
          </div>
        );
      }

      if (status === "completed") {
        if (isCancelled) {
          return (
            <div className="flex items-center gap-2 text-yellow-600 mb-4 p-3 bg-yellow-50 rounded-md">
              <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              Tool Call Cancelled
            </div>
          );
        }
        if (hasFeedback) {
          return (
            <div className="flex flex-col gap-2 text-purple-600 mb-4 p-3 bg-purple-50 rounded-md">
              <div className="flex items-center gap-2 font-medium">
                <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
                </svg>
                Feedback provided:
              </div>
              <div className="text-sm pl-7">{result}</div>
            </div>
          );
        }
        return (
          <div className="flex items-center gap-2 text-green-600 mb-4 p-3 bg-green-50 rounded-md">
            <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            Email Successfully Sent
          </div>
        );
      }

      if (status === "error") {
        return (
          <div className="flex items-center gap-2 text-red-600 mb-4 p-3 bg-red-50 rounded-md">
            <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
            Could not send email
          </div>
        );
      }

      return null;
    };

    const isEditable = status === "interrupted";

    return (
      <div className={`rounded-lg border-2 ${getBorderColor()} p-4 bg-white w-full max-w-full`}>
        {status === "interrupted" && (
          <div className="flex items-center gap-2 text-purple-600 mb-4 p-3 bg-purple-50 rounded-md font-medium">
            <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Awaiting user input...
          </div>
        )}
        {getStatusBanner()}

        <div className="flex flex-col gap-4 w-full">
          {/* Recipients Section */}
          <div className="relative">
            <div className="flex justify-between items-center mb-2">
              <label className="text-sm font-medium text-gray-700">To:</label>
              <button
                onClick={() => copyToClipboard(recipients.join(", "))}
                className="opacity-0 hover:opacity-100 transition-opacity p-1 hover:bg-gray-100 rounded"
                title="Copy recipients"
              >
                <svg className="h-4 w-4 text-gray-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </button>
            </div>
            {isEditable ? (
              <input
                type="text"
                value={recipients.join(", ")}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setRecipients(e.target.value.split(",").map((r: string) => r.trim()))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="recipient@example.com"
              />
            ) : (
              <div className="px-3 py-2 bg-gray-50 rounded-md text-gray-700 border border-gray-200">
                {recipients.join(", ")}
              </div>
            )}
          </div>

          {/* Subject Section */}
          <div className="relative">
            <div className="flex justify-between items-center mb-2">
              <label className="text-sm font-medium text-gray-700">Subject:</label>
              <button
                onClick={() => copyToClipboard(subject)}
                className="opacity-0 hover:opacity-100 transition-opacity p-1 hover:bg-gray-100 rounded"
                title="Copy subject"
              >
                <svg className="h-4 w-4 text-gray-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </button>
            </div>
            {isEditable ? (
              <input
                type="text"
                value={subject}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSubject(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Email subject"
              />
            ) : (
              <div className="px-3 py-2 bg-gray-50 rounded-md text-gray-700 border border-gray-200 font-medium">
                {subject}
              </div>
            )}
          </div>

          {/* Content Section */}
          <div className="relative">
            <div className="flex justify-between items-center mb-2">
              <label className="text-sm font-medium text-gray-700">Message:</label>
              <button
                onClick={() => copyToClipboard(content)}
                className="opacity-0 hover:opacity-100 transition-opacity p-1 hover:bg-gray-100 rounded"
                title="Copy content"
              >
                <svg className="h-4 w-4 text-gray-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </button>
            </div>
            {isEditable ? (
              <textarea
                value={content}
                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setContent(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[400px] font-mono text-sm"
                placeholder="Email content..."
              />
            ) : (
              <div className="px-3 py-2 bg-gray-50 rounded-md text-gray-700 border border-gray-200 min-h-[400px] whitespace-pre-wrap font-mono text-sm">
                {content}
              </div>
            )}
          </div>

          {/* Send Button - Only shown in interrupted state */}
          {isEditable && (
            <div className="flex gap-2 self-end">
              {openInGmailButton(values.email?.id || "", true)}
              <button
                onClick={handleSendEmail}
                className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors font-medium"
              >
                Send Email
              </button>
            </div>
          )}

          {/* Feedback Section - Only shown in interrupted state */}
          {isEditable && (
            <div className="mt-6 pt-6 border-t-2 border-gray-200">
              <div className="flex flex-col gap-3">
                <label className="text-sm font-medium text-gray-600 italic">
                  Ask your assistant to edit this draft, or take a different action
                </label>
                <div className="flex gap-2">
                  <textarea
                    value={feedback}
                    onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setFeedback(e.target.value)}
                    onKeyDown={(e: React.KeyboardEvent<HTMLTextAreaElement>) => {
                      if ((e.metaKey || e.ctrlKey) && e.key === "Enter" && feedback.trim()) {
                        e.preventDefault();
                        handleSubmitFeedback();
                      }
                    }}
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 min-h-[80px] bg-purple-50/30"
                    placeholder="e.g., 'Make the tone more formal' or 'Add a closing paragraph'"
                  />
                </div>
                <button
                  onClick={handleSubmitFeedback}
                  disabled={!feedback.trim()}
                  className="self-end px-3 py-1.5 text-sm bg-purple-600 text-white rounded-md hover:bg-purple-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-purple-600"
                >
                  Submit Feedback
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    );
}

const GetEventsForDaysComponent = () => {
    const { meta } = useStreamContext<
      {},
      { MetaType: {
        args?: Record<string, any>,
        result?: string | any[],
        status?: "pending" | "completed" | "error" | "interrupted"
      }}
    >();
    const args = meta?.args || {};
    const status = meta?.status || "pending";
    const result = meta?.result;

    const dateStr = args.date_str || "the requested date";

    // Parse events from result
    const getEvents = () => {
      if (!result) return [];
      if (typeof result === 'string') {
        try {
          return JSON.parse(result);
        } catch {
          return [];
        }
      }
      if (Array.isArray(result)) return result;
      return [];
    };

    const events = getEvents();

    // Pending state
    if (status === "pending") {
      return (
        <div className="rounded-lg border-2 border-blue-500 p-4 bg-white w-full max-w-full">
          <div className="flex items-center gap-2 text-blue-600 p-3 bg-blue-50 rounded-md">
            <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Searching for events for {dateStr}
          </div>
        </div>
      );
    }

    // Error state
    if (status === "error") {
      return (
        <div className="rounded-lg border-2 border-red-500 p-4 bg-white w-full max-w-full">
          <div className="flex items-center gap-2 text-red-600 p-3 bg-red-50 rounded-md">
            <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
            {typeof result === 'string' ? result : "Failed to retrieve events"}
          </div>
        </div>
      );
    }

    // Completed state
    return (
      <div className="rounded-lg border-2 border-green-500 p-4 bg-white w-full max-w-full">
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-2 text-green-600 font-semibold text-lg">
            <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            Events for {dateStr}
          </div>

          {events.length === 0 ? (
            <div className="text-gray-500 italic py-4">No events found for this date</div>
          ) : (
            <div className="flex flex-col gap-2">
              {events.map((event: any, index: number) => (
                <div
                  key={event.id || index}
                  className="flex flex-col gap-1 p-3 bg-gray-50 rounded-md border border-gray-200 hover:bg-gray-100 transition-colors"
                >
                  <div className="font-medium text-gray-900">{event.summary}</div>
                  <div className="text-sm text-gray-600 flex items-center gap-2">
                    <svg className="h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    {event.start_time} - {event.end_time}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    );
}

export default {
    email_marked_as_read: EmailMarkedAsReadComponent,
    write_email_response: WriteEmailResponseComponent,
    message_user: MessageUserComponent,
    send_calendar_invite: SendCalendarInviteComponent,
    start_new_email_thread: StartNewEmailThreadComponent,
    get_events_for_days: GetEventsForDaysComponent,
};