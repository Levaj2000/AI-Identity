import { useParams } from "react-router";
import BlogPage from "../components/BlogPage";
import BlogPost from "../components/BlogPost";

export default function Blog() {
  const { slug } = useParams<{ slug: string }>();
  return slug ? <BlogPost /> : <BlogPage />;
}
