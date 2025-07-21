// import React from 'react';
import useBaseUrl from '@docusaurus/useBaseUrl';

export default function NextstepWithImage() {
  const imageUrl = useBaseUrl('/img/next.png');
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '1rem' }}>
      <img src={imageUrl} alt="Next Steps Icon" width={40} height={40} />
      <h2 style={{ margin: 0 }}>Next Steps</h2>
    </div>
  );
}
