import { redirect } from "next/navigation";

// Redirect root to the setup/chat page
export default function HomePage() {
  redirect("/setup");
}
