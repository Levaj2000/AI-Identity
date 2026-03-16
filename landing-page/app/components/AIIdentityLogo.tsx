interface LogoProps {
  className?: string;
  variant?: 'light' | 'dark' | 'primary';
}

// Logo Variation 1: "Infinite Loop" - Overlapping geometric circles creating an infinity-like mark
export function AIIdentityLogo1({ className = '', variant = 'primary' }: LogoProps) {
  const colors = {
    light: '#FFFFFF',
    dark: '#0A0A0B',
    primary: '#00FFC2'
  };

  const fillColor = colors[variant];

  return (
    <svg
      viewBox="0 0 200 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Abstract geometric mark - two intersecting circles */}
      <g>
        <circle
          cx="18"
          cy="24"
          r="10"
          stroke={fillColor}
          strokeWidth="2"
          fill="none"
          opacity="0.8"
        />
        <circle
          cx="30"
          cy="24"
          r="10"
          stroke={fillColor}
          strokeWidth="2"
          fill="none"
        />
        {/* Center intersection point */}
        <circle
          cx="24"
          cy="24"
          r="2"
          fill={fillColor}
        />
      </g>

      {/* Text: AI Identity */}
      <g transform="translate(50, 14)">
        <text
          x="0"
          y="16"
          fill={fillColor}
          fontFamily="Inter, sans-serif"
          fontWeight="700"
          fontSize="22"
          letterSpacing="-0.5"
        >
          AI Identity
        </text>
      </g>
    </svg>
  );
}

// Logo Variation 2: "Set Theory" - Mathematical set intersection symbol
export function AIIdentityLogo2({ className = '', variant = 'primary' }: LogoProps) {
  const colors = {
    light: '#FFFFFF',
    dark: '#0A0A0B',
    primary: '#00FFC2'
  };

  const fillColor = colors[variant];

  return (
    <svg
      viewBox="0 0 200 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Mathematical symbol - intersection/union */}
      <g>
        {/* Left arc */}
        <path
          d="M12 12 Q12 36 24 36"
          stroke={fillColor}
          strokeWidth="2.5"
          fill="none"
          strokeLinecap="round"
        />
        {/* Right arc */}
        <path
          d="M36 12 Q36 36 24 36"
          stroke={fillColor}
          strokeWidth="2.5"
          fill="none"
          strokeLinecap="round"
        />
        {/* Minimal dots at endpoints */}
        <circle cx="12" cy="12" r="2" fill={fillColor} />
        <circle cx="36" cy="12" r="2" fill={fillColor} />
      </g>

      {/* Text: AI Identity */}
      <g transform="translate(52, 14)">
        <text
          x="0"
          y="16"
          fill={fillColor}
          fontFamily="Inter, sans-serif"
          fontWeight="700"
          fontSize="22"
          letterSpacing="-0.5"
        >
          AI Identity
        </text>
      </g>
    </svg>
  );
}

// Logo Variation 3: "Neural Grid" - Minimalist connected nodes forming abstract network
export function AIIdentityLogo3({ className = '', variant = 'primary' }: LogoProps) {
  const colors = {
    light: '#FFFFFF',
    dark: '#0A0A0B',
    primary: '#00FFC2'
  };

  const fillColor = colors[variant];

  return (
    <svg
      viewBox="0 0 200 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Abstract network - minimal connected nodes */}
      <g>
        {/* Geometric triangle of nodes */}
        <circle cx="24" cy="12" r="2.5" fill={fillColor} />
        <circle cx="16" cy="32" r="2.5" fill={fillColor} />
        <circle cx="32" cy="32" r="2.5" fill={fillColor} />

        {/* Connecting lines */}
        <path
          d="M24 14.5 L16 29.5 M24 14.5 L32 29.5 M16 32 L32 32"
          stroke={fillColor}
          strokeWidth="1.5"
          opacity="0.5"
        />

        {/* Center point */}
        <circle cx="24" cy="24" r="1.5" fill={fillColor} opacity="0.6" />
      </g>

      {/* Text: AI Identity */}
      <g transform="translate(48, 14)">
        <text
          x="0"
          y="16"
          fill={fillColor}
          fontFamily="Inter, sans-serif"
          fontWeight="700"
          fontSize="22"
          letterSpacing="-0.5"
        >
          AI Identity
        </text>
      </g>
    </svg>
  );
}

// Icon-only variations for compact spaces
export function AIIdentityIcon1({ className = '', variant = 'primary' }: LogoProps) {
  const colors = {
    light: '#FFFFFF',
    dark: '#0A0A0B',
    primary: '#00FFC2'
  };

  const fillColor = colors[variant];

  return (
    <svg
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <circle cx="18" cy="24" r="10" stroke={fillColor} strokeWidth="2.5" fill="none" opacity="0.8" />
      <circle cx="30" cy="24" r="10" stroke={fillColor} strokeWidth="2.5" fill="none" />
      <circle cx="24" cy="24" r="3" fill={fillColor} />
    </svg>
  );
}

export function AIIdentityIcon2({ className = '', variant = 'primary' }: LogoProps) {
  const colors = {
    light: '#FFFFFF',
    dark: '#0A0A0B',
    primary: '#00FFC2'
  };

  const fillColor = colors[variant];

  return (
    <svg
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <path
        d="M12 8 Q12 40 24 40"
        stroke={fillColor}
        strokeWidth="3"
        fill="none"
        strokeLinecap="round"
      />
      <path
        d="M36 8 Q36 40 24 40"
        stroke={fillColor}
        strokeWidth="3"
        fill="none"
        strokeLinecap="round"
      />
      <circle cx="12" cy="8" r="2.5" fill={fillColor} />
      <circle cx="36" cy="8" r="2.5" fill={fillColor} />
    </svg>
  );
}

export function AIIdentityIcon3({ className = '', variant = 'primary' }: LogoProps) {
  const colors = {
    light: '#FFFFFF',
    dark: '#0A0A0B',
    primary: '#00FFC2'
  };

  const fillColor = colors[variant];

  return (
    <svg
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <circle cx="24" cy="12" r="3.5" fill={fillColor} />
      <circle cx="12" cy="36" r="3.5" fill={fillColor} />
      <circle cx="36" cy="36" r="3.5" fill={fillColor} />
      <path
        d="M24 15.5 L12 32.5 M24 15.5 L36 32.5 M12 36 L36 36"
        stroke={fillColor}
        strokeWidth="2"
        opacity="0.5"
      />
      <circle cx="24" cy="24" r="2" fill={fillColor} opacity="0.6" />
    </svg>
  );
}

// Logo Variation 4: "Ai" + Fingerprint - Combining imported Figma elements
export function AIIdentityLogo4({ className = '', variant = 'primary' }: LogoProps) {
  const colors = {
    light: '#FFFFFF',
    dark: '#0A0A0B',
    primary: '#00FFC2'
  };

  const fillColor = colors[variant];

  return (
    <svg
      viewBox="0 0 220 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Fingerprint icon from imported Touch ID */}
      <g transform="translate(0, 5) scale(0.95)">
        <path d="M12.091 36.2432C15.0191 33.8866 16.6259 30.1372 16.608 25.9773C16.5902 22.8349 15.4654 20.889 15.4654 19.175C15.4654 16.9254 17.0544 15.4257 19.3753 15.4257C22.9462 15.4257 24.1066 19.4964 24.2137 24.3169C24.3744 29.8873 22.357 34.6007 19.7146 36.9216C19.2861 37.2787 19.1969 37.8323 19.4825 38.2785C19.8218 38.7606 20.518 38.8498 20.9822 38.4213C23.7675 35.8861 26.1241 30.3157 26.0884 24.1741C26.0705 18.1752 24.3744 13.426 19.3753 13.426C16.0546 13.426 13.5015 15.6399 13.5015 18.9964C13.5015 21.0138 14.5727 23.4956 14.5906 25.9773C14.6084 29.5124 13.2872 32.6904 10.8413 34.672C10.3592 35.0649 10.2878 35.6362 10.5913 36.0825C10.9662 36.6002 11.609 36.6538 12.091 36.2432Z" fill={fillColor} />
        <path d="M12.1621 24.2098C11.7158 22.9956 10.9838 21.4603 10.9838 19.3893C10.9838 14.6401 14.6795 10.9444 19.4285 10.9444C21.2496 10.9444 21.821 11.1408 23.4101 11.9085C23.9635 12.1584 24.4633 11.9977 24.6598 11.605C24.9275 11.1051 24.7847 10.498 24.1777 10.141C22.9994 9.44466 21.1961 8.92688 19.4285 8.92688C13.5725 8.92688 8.96627 13.5332 8.96627 19.3893C8.96627 21.6387 9.57329 23.4598 10.1982 24.9774C10.4481 25.5667 10.9838 25.8522 11.6265 25.5844C12.1621 25.3703 12.3585 24.799 12.1621 24.2098Z" fill={fillColor} />
        <path d="M2.05689 25.3881C2.57466 25.2274 2.82461 24.6919 2.68177 24.0847C2.23543 22.2815 1.96763 20.3712 2.05689 17.8716C2.07475 17.2111 1.71767 16.854 1.18206 16.8183C0.48576 16.7647 0.11083 17.1932 0.0572689 17.7467C-0.103415 19.7641 0.0572689 22.1744 0.753567 24.656C0.932104 25.2632 1.50343 25.5667 2.05689 25.3881ZM1.27133 14.7472C1.78909 14.9436 2.44968 14.7115 2.69964 14.0331C5.57409 5.99888 12.4478 1.99963 19.4286 1.99963C22.6066 1.99963 25.1062 2.64236 27.2307 3.85643C27.8377 4.2135 28.5162 4.2135 28.784 3.62432C29.0698 2.99943 28.7483 2.60665 28.3019 2.32099C25.5883 0.624883 22.8388 0 19.4286 0C11.3587 0 4.03867 4.30277 0.753567 13.0511C0.414344 13.9438 0.753567 14.5687 1.27133 14.7472ZM38.4072 21.2281C38.9786 21.2281 39.3892 20.7639 39.3356 20.139C38.5321 12.8726 36.1399 8.28416 32.0156 4.67769C31.4978 4.2135 30.8729 4.35632 30.5694 4.71339C30.2301 5.08833 30.1945 5.67751 30.7301 6.15956C34.2473 9.44467 36.8004 13.6939 37.4074 20.1749C37.4789 20.7639 37.8359 21.2281 38.4072 21.2281Z" fill={fillColor} />
        <path d="M4.1279 30.5658C4.46711 31.03 5.14557 31.1548 5.64548 30.7263C6.93094 29.6372 7.57367 27.8876 7.57367 26.0665C7.57367 23.6028 6.50246 22.353 6.50246 19.2821C6.50246 12.2834 12.3228 6.46306 19.3214 6.46306C27.7664 6.46306 33.2117 13.3725 33.2297 23.5669C33.2297 27.5485 32.5689 30.3692 31.9084 31.994C31.6762 32.5474 31.8905 33.1366 32.3547 33.3865C32.8547 33.6008 33.5509 33.4222 33.7651 32.8331C34.4615 30.9406 35.2292 27.834 35.2292 23.5492C35.2292 12.1763 28.9626 4.46343 19.3214 4.46343C11.2159 4.46343 4.50283 11.1943 4.50283 19.2821C4.50283 22.21 5.60975 24.1918 5.62762 26.0486C5.62762 27.2627 5.18127 28.4233 4.34213 29.1553C3.91365 29.5123 3.84224 30.155 4.1279 30.5658Z" fill={fillColor} />
        <path d="M16.2688 37.6716C17.6792 36.6538 19.4288 34.315 20.1073 32.0297C20.2324 31.637 20.1431 30.9764 19.5718 30.7799C18.9647 30.5658 18.4469 30.8693 18.2862 31.3335C17.3757 33.7259 16.2509 35.1364 15.0547 36.0647C14.6084 36.4218 14.4834 37.0109 14.7869 37.475C15.0726 37.9751 15.7689 38.0464 16.2688 37.6716ZM21.1251 27.8697C21.6249 25.4596 21.4286 22.3708 20.5538 19.6928C20.3216 19.0322 19.8038 18.7465 19.2504 18.9251C18.7327 19.1035 18.4113 19.5856 18.6076 20.2105C19.4288 22.7993 19.5718 25.3524 19.161 27.6021C19.0539 28.1375 19.2681 28.6553 19.893 28.7447C20.4644 28.8517 21 28.5125 21.1251 27.8697Z" fill={fillColor} />
        <path d="M8.34137 33.8866C9.66256 33.2082 11.4658 30.8871 11.9657 29.0482C12.1085 28.5482 11.8764 27.9412 11.323 27.7626C10.8231 27.5842 10.2875 27.8877 10.0911 28.459C9.60899 30.0302 8.76987 31.2085 7.44869 32.1012C6.80595 32.5475 6.71668 33.101 6.91307 33.5117C7.12732 33.9579 7.69864 34.2079 8.34137 33.8866ZM26.2131 14.301C27.9448 16.8183 28.8019 20.2998 28.8019 24.5133C28.8019 29.0124 27.5521 33.2617 25.6059 35.6898C25.2847 36.1184 25.2489 36.7253 25.6418 37.118C26.0701 37.5109 26.8022 37.493 27.1592 37.0109C29.3374 34.0651 30.7657 29.3874 30.7657 24.4418C30.7657 19.0323 29.6052 15.8185 27.9806 13.2297C27.6057 12.6584 26.9808 12.4799 26.4807 12.7477C25.963 13.0333 25.8025 13.6939 26.2131 14.301Z" fill={fillColor} />
      </g>

      {/* "Ai" text adapted from Adobe Illustrator import */}
      <g transform="translate(52, 12)">
        <text
          x="0"
          y="16"
          fill={fillColor}
          fontFamily="Inter, sans-serif"
          fontWeight="700"
          fontSize="22"
          letterSpacing="-0.5"
        >
          AI Identity
        </text>
      </g>
    </svg>
  );
}

// Icon-only version with fingerprint
export function AIIdentityIcon4({ className = '', variant = 'primary' }: LogoProps) {
  const colors = {
    light: '#FFFFFF',
    dark: '#0A0A0B',
    primary: '#00FFC2'
  };

  const fillColor = colors[variant];

  return (
    <svg
      viewBox="0 0 40 38.725"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Fingerprint paths from Touch ID import */}
      <path d="M12.091 36.2432C15.0191 33.8866 16.6259 30.1372 16.608 25.9773C16.5902 22.8349 15.4654 20.889 15.4654 19.175C15.4654 16.9254 17.0544 15.4257 19.3753 15.4257C22.9462 15.4257 24.1066 19.4964 24.2137 24.3169C24.3744 29.8873 22.357 34.6007 19.7146 36.9216C19.2861 37.2787 19.1969 37.8323 19.4825 38.2785C19.8218 38.7606 20.518 38.8498 20.9822 38.4213C23.7675 35.8861 26.1241 30.3157 26.0884 24.1741C26.0705 18.1752 24.3744 13.426 19.3753 13.426C16.0546 13.426 13.5015 15.6399 13.5015 18.9964C13.5015 21.0138 14.5727 23.4956 14.5906 25.9773C14.6084 29.5124 13.2872 32.6904 10.8413 34.672C10.3592 35.0649 10.2878 35.6362 10.5913 36.0825C10.9662 36.6002 11.609 36.6538 12.091 36.2432Z" fill={fillColor} />
      <path d="M12.1621 24.2098C11.7158 22.9956 10.9838 21.4603 10.9838 19.3893C10.9838 14.6401 14.6795 10.9444 19.4285 10.9444C21.2496 10.9444 21.821 11.1408 23.4101 11.9085C23.9635 12.1584 24.4633 11.9977 24.6598 11.605C24.9275 11.1051 24.7847 10.498 24.1777 10.141C22.9994 9.44466 21.1961 8.92688 19.4285 8.92688C13.5725 8.92688 8.96627 13.5332 8.96627 19.3893C8.96627 21.6387 9.57329 23.4598 10.1982 24.9774C10.4481 25.5667 10.9838 25.8522 11.6265 25.5844C12.1621 25.3703 12.3585 24.799 12.1621 24.2098Z" fill={fillColor} />
      <path d="M2.05689 25.3881C2.57466 25.2274 2.82461 24.6919 2.68177 24.0847C2.23543 22.2815 1.96763 20.3712 2.05689 17.8716C2.07475 17.2111 1.71767 16.854 1.18206 16.8183C0.48576 16.7647 0.11083 17.1932 0.0572689 17.7467C-0.103415 19.7641 0.0572689 22.1744 0.753567 24.656C0.932104 25.2632 1.50343 25.5667 2.05689 25.3881ZM1.27133 14.7472C1.78909 14.9436 2.44968 14.7115 2.69964 14.0331C5.57409 5.99888 12.4478 1.99963 19.4286 1.99963C22.6066 1.99963 25.1062 2.64236 27.2307 3.85643C27.8377 4.2135 28.5162 4.2135 28.784 3.62432C29.0698 2.99943 28.7483 2.60665 28.3019 2.32099C25.5883 0.624883 22.8388 0 19.4286 0C11.3587 0 4.03867 4.30277 0.753567 13.0511C0.414344 13.9438 0.753567 14.5687 1.27133 14.7472ZM38.4072 21.2281C38.9786 21.2281 39.3892 20.7639 39.3356 20.139C38.5321 12.8726 36.1399 8.28416 32.0156 4.67769C31.4978 4.2135 30.8729 4.35632 30.5694 4.71339C30.2301 5.08833 30.1945 5.67751 30.7301 6.15956C34.2473 9.44467 36.8004 13.6939 37.4074 20.1749C37.4789 20.7639 37.8359 21.2281 38.4072 21.2281Z" fill={fillColor} />
      <path d="M4.1279 30.5658C4.46711 31.03 5.14557 31.1548 5.64548 30.7263C6.93094 29.6372 7.57367 27.8876 7.57367 26.0665C7.57367 23.6028 6.50246 22.353 6.50246 19.2821C6.50246 12.2834 12.3228 6.46306 19.3214 6.46306C27.7664 6.46306 33.2117 13.3725 33.2297 23.5669C33.2297 27.5485 32.5689 30.3692 31.9084 31.994C31.6762 32.5474 31.8905 33.1366 32.3547 33.3865C32.8547 33.6008 33.5509 33.4222 33.7651 32.8331C34.4615 30.9406 35.2292 27.834 35.2292 23.5492C35.2292 12.1763 28.9626 4.46343 19.3214 4.46343C11.2159 4.46343 4.50283 11.1943 4.50283 19.2821C4.50283 22.21 5.60975 24.1918 5.62762 26.0486C5.62762 27.2627 5.18127 28.4233 4.34213 29.1553C3.91365 29.5123 3.84224 30.155 4.1279 30.5658Z" fill={fillColor} />
      <path d="M16.2688 37.6716C17.6792 36.6538 19.4288 34.315 20.1073 32.0297C20.2324 31.637 20.1431 30.9764 19.5718 30.7799C18.9647 30.5658 18.4469 30.8693 18.2862 31.3335C17.3757 33.7259 16.2509 35.1364 15.0547 36.0647C14.6084 36.4218 14.4834 37.0109 14.7869 37.475C15.0726 37.9751 15.7689 38.0464 16.2688 37.6716ZM21.1251 27.8697C21.6249 25.4596 21.4286 22.3708 20.5538 19.6928C20.3216 19.0322 19.8038 18.7465 19.2504 18.9251C18.7327 19.1035 18.4113 19.5856 18.6076 20.2105C19.4288 22.7993 19.5718 25.3524 19.161 27.6021C19.0539 28.1375 19.2681 28.6553 19.893 28.7447C20.4644 28.8517 21 28.5125 21.1251 27.8697Z" fill={fillColor} />
      <path d="M8.34137 33.8866C9.66256 33.2082 11.4658 30.8871 11.9657 29.0482C12.1085 28.5482 11.8764 27.9412 11.323 27.7626C10.8231 27.5842 10.2875 27.8877 10.0911 28.459C9.60899 30.0302 8.76987 31.2085 7.44869 32.1012C6.80595 32.5475 6.71668 33.101 6.91307 33.5117C7.12732 33.9579 7.69864 34.2079 8.34137 33.8866ZM26.2131 14.301C27.9448 16.8183 28.8019 20.2998 28.8019 24.5133C28.8019 29.0124 27.5521 33.2617 25.6059 35.6898C25.2847 36.1184 25.2489 36.7253 25.6418 37.118C26.0701 37.5109 26.8022 37.493 27.1592 37.0109C29.3374 34.0651 30.7657 29.3874 30.7657 24.4418C30.7657 19.0323 29.6052 15.8185 27.9806 13.2297C27.6057 12.6584 26.9808 12.4799 26.4807 12.7477C25.963 13.0333 25.8025 13.6939 26.2131 14.301Z" fill={fillColor} />
    </svg>
  );
}

// Logo Variation 5: Three Rectangles - Ultra minimalist bar chart style
export function AIIdentityLogo5({ className = '', variant = 'primary' }: LogoProps) {
  const colors = {
    light: '#FFFFFF',
    dark: '#0A0A0B',
    primary: '#00FFC2'
  };

  const fillColor = colors[variant];

  return (
    <svg
      viewBox="0 0 400 200"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Three rectangles - bar chart style with varying heights, centered */}
      <rect x="140" y="50" width="30" height="45" fill={fillColor} rx="2" />
      <rect x="180" y="20" width="30" height="75" fill={fillColor} rx="2" />
      <rect x="220" y="35" width="30" height="60" fill={fillColor} rx="2" />

      {/* Text: AI IDENTITY in Inter Bold, centered */}
      <text
        x="200"
        y="150"
        fill={fillColor}
        fontFamily="Inter, sans-serif"
        fontWeight="700"
        fontSize="48"
        letterSpacing="4"
        textAnchor="middle"
      >
        AI IDENTITY
      </text>
    </svg>
  );
}

// Icon-only version with three rectangles in bar chart style
export function AIIdentityIcon5({ className = '', variant = 'primary' }: LogoProps) {
  const colors = {
    light: '#FFFFFF',
    dark: '#0A0A0B',
    primary: '#00FFC2'
  };

  const fillColor = colors[variant];

  return (
    <svg
      viewBox="0 0 100 95"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Three rectangles in bar chart pattern - centered */}
      <rect x="20" y="50" width="15" height="45" fill={fillColor} rx="2" />
      <rect x="42.5" y="20" width="15" height="75" fill={fillColor} rx="2" />
      <rect x="65" y="35" width="15" height="60" fill={fillColor} rx="2" />
    </svg>
  );
}
