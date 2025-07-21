import React from 'react';
import useBaseUrl from '@docusaurus/useBaseUrl';

export default function HeaderWithImage() {
  const imageUrl = useBaseUrl('/img/image.png');
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '1rem' }}>
      <img src={imageUrl} alt=" Logo" width={40} height={40} />
      <h1 style={{ margin: 0 }}>Getting Started</h1>
    </div>
  );
}
