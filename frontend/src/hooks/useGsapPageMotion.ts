import { useLayoutEffect } from 'react';
import type { RefObject } from 'react';
import { gsap } from 'gsap';

export const useGsapPageMotion = (
  containerRef: RefObject<HTMLElement | null>,
  deps: ReadonlyArray<unknown> = [],
) => {
  useLayoutEffect(() => {
    const root = containerRef.current;
    if (!root) return;

    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReduced) return;

    const ctx = gsap.context(() => {
      const q = gsap.utils.selector(root);
      const headline = q('[data-motion="headline"]');
      const panel = q('[data-motion="panel"]');
      const cards = q('[data-motion="card"]');
      const rows = q('[data-motion="row"]');
      const blobs = q('[data-motion="blob"]');

      const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });
      tl.fromTo(headline, { autoAlpha: 0.01, y: 16 }, { autoAlpha: 1, y: 0, duration: 0.78 })
        .fromTo(panel, { autoAlpha: 0.01, y: 14, scale: 0.994 }, { autoAlpha: 1, y: 0, scale: 1, duration: 0.72, stagger: 0.1 }, '-=0.46')
        .fromTo(cards, { autoAlpha: 0.01, y: 12 }, { autoAlpha: 1, y: 0, duration: 0.62, stagger: 0.08 }, '-=0.42')
        .fromTo(rows, { autoAlpha: 0.01, y: 8 }, { autoAlpha: 1, y: 0, duration: 0.54, stagger: 0.06 }, '-=0.4');

      blobs.forEach((blob, idx) => {
        gsap.to(blob, {
          y: idx % 2 === 0 ? -10 : 10,
          x: idx % 2 === 0 ? 8 : -8,
          duration: 10 + idx,
          ease: 'sine.inOut',
          repeat: -1,
          yoyo: true,
        });
      });
    }, root);

    return () => ctx.revert();
  }, [containerRef, ...deps]);
};
