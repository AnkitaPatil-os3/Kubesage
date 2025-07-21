// import React from 'react';

// export default function PrerequisitesWithImage() {
//   return (
//     <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '1rem' }}>
//       <img src="/img/prerequiisites.png" alt="Prerequisites Icon" width={40} height={40} />
//       <h2 style={{ margin: 0 }}>Prerequisites</h2>
//     </div>
//   );
// }
import React from 'react';
import useBaseUrl from '@docusaurus/useBaseUrl';

export default function PrerequisitesWithImage() {
  const imageUrl = useBaseUrl('/img/prerequiisites.png');
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '1rem' }}>
      <img src={imageUrl} alt="Prerequisites Icon" width={40} height={40} />
      <h2 style={{ margin: 0 }}>Prerequisites</h2>
    </div>
  );
}
