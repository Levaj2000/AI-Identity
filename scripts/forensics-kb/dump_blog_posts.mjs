import { blogPosts } from "../../landing-page/src/data/blog-posts.ts";
process.stdout.write(JSON.stringify(blogPosts, null, 2));
