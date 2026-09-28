import { defineMiddleware } from 'astro:middleware';

function backendOrigin(): string {
  const fromEnv =
    (typeof process !== 'undefined' && process.env.BACKEND_URL) ||
    (import.meta.env.BACKEND_URL as string | undefined);
  return (fromEnv || 'http://localhost:8000').replace(/\/+$/, '');
}

export const onRequest = defineMiddleware(async (context, next) => {
  const { pathname, search } = context.url;

  if (pathname.startsWith('/media/') || pathname.startsWith('/static/')) {
    const target = `${backendOrigin()}${pathname}${search}`;
    try {
      const upstream = await fetch(target);
      const headers = new Headers();
      const contentType = upstream.headers.get('content-type');
      const cacheControl = upstream.headers.get('cache-control');
      if (contentType) headers.set('content-type', contentType);
      if (cacheControl) headers.set('cache-control', cacheControl);
      return new Response(upstream.body, { status: upstream.status, headers });
    } catch {
      return new Response('Arquivo indisponível', { status: 502 });
    }
  }

  return next();
});
