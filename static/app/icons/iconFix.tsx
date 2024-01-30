import {forwardRef} from 'react';

import type {SVGIconProps} from './svgIcon';
import {SvgIcon} from './svgIcon';

const IconFix = forwardRef<SVGSVGElement, SVGIconProps>((props, ref) => {
  return (
    <SvgIcon {...props} ref={ref}>
      <path d="M2.68,16a2.64,2.64,0,0,1-1.86-.77,2.61,2.61,0,0,1-.77-1.86,2.58,2.58,0,0,1,.77-1.86L5.71,6.57l0-.05a4.74,4.74,0,0,1,.79-5.25A4.76,4.76,0,0,1,11.75.5.73.73,0,0,1,12.2,1a.74.74,0,0,1-.2.68L9.72,4l.61,1.67L12,6.28,14.28,4A.74.74,0,0,1,15,3.8a.73.73,0,0,1,.54.45,4.76,4.76,0,0,1-.77,5.27,4.76,4.76,0,0,1-5.28.78h0L4.54,15.18A2.62,2.62,0,0,1,2.68,16Zm6.9-14.4a2.86,2.86,0,0,0-2,.78A3.32,3.32,0,0,0,7.09,6l.19.53a.73.73,0,0,1-.18.78L1.88,12.52a1.13,1.13,0,0,0,0,1.6,1.15,1.15,0,0,0,1.6,0L8.71,8.9a.73.73,0,0,1,.78-.18l.5.18a3.32,3.32,0,0,0,3.68-.44A2.93,2.93,0,0,0,14.42,6l-1.7,1.7a.73.73,0,0,1-.79.17L9.49,7a.69.69,0,0,1-.44-.44l-.9-2.44a.73.73,0,0,1,.17-.79L10,1.58Z" />
    </SvgIcon>
  );
});

IconFix.displayName = 'IconFix';

export {IconFix};
