import React, { useState } from 'react';

type InstitutionalLogoProps = {
  size?: number;
  radius?: number;
  withLabel?: boolean;
  labelColor?: string;
};

export const InstitutionalLogo: React.FC<InstitutionalLogoProps> = ({
  size = 92,
  radius,
  withLabel = false,
  labelColor = '#385162',
}) => {
  const [imgError, setImgError] = useState(false);
  const boxSize = Math.round(size * 1.12);
  const boxRadius = radius ?? Math.max(10, Math.round(boxSize * 0.12));
  const innerSize = Math.round(size * 0.68);

  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '12px' }}>
      <div
        style={{
          width: `${boxSize}px`,
          height: `${boxSize}px`,
          borderRadius: `${boxRadius}px`,
          display: 'grid',
          placeItems: 'center',
          boxShadow: 'none',
          overflow: 'visible',
          flexShrink: 0,
          background: 'transparent',
        }}
      >
        {!imgError ? (
          <img
            src="/assets/logo-ucundinamarca.png"
            alt="Logo Universidad de Cundinamarca"
            style={{
              width: `${size}px`,
              height: `${size}px`,
              objectFit: 'contain',
              filter: 'drop-shadow(0 6px 14px rgba(16, 41, 57, 0.22))',
            }}
            onError={() => setImgError(true)}
          />
        ) : (
          <div
            style={{
              width: `${innerSize}px`,
              height: `${innerSize}px`,
              borderRadius: `${Math.round(innerSize * 0.2)}px`,
              display: 'grid',
              placeItems: 'center',
              background: 'linear-gradient(135deg, #35566d 0%, #55776f 100%)',
              color: '#ffffff',
              fontWeight: 800,
              letterSpacing: '0.03em',
              fontSize: `${Math.max(16, Math.round(size * 0.18))}px`,
              fontFamily: 'var(--font-heading)',
            }}
          >
            UC
          </div>
        )}
      </div>

      {withLabel && (
        <div style={{ lineHeight: 1.1 }}>
          <p style={{ margin: 0, color: labelColor, fontSize: '12px', fontWeight: 700, letterSpacing: '0.06em' }}>
            UNIVERSIDAD DE CUNDINAMARCA
          </p>
          <p style={{ margin: '4px 0 0', color: labelColor, opacity: 0.85, fontSize: '11px' }}>
            Ascenso Pro
          </p>
        </div>
      )}
    </div>
  );
};
