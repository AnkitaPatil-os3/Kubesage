// import React from 'react';

// export default function InsideWithImage() {
//   return (
//     <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '1rem' }}>
//       <img src="/img/brain.png" alt="Brain Icon" width={40} height={40} />
//       <h2 style={{ margin: 0 }}>What is inside?</h2>
//     </div>
//   );
// }
import React from 'react';
import useBaseUrl from '@docusaurus/useBaseUrl';

export default function InsideWithImage() {
  const imageUrl = useBaseUrl('/img/brain.png');
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '1rem' }}>
      <img src={imageUrl} alt="Brain Icon" width={40} height={40} />
      <h2 style={{ margin: 0 }}>What is inside?</h2>
    </div>
  );
}
