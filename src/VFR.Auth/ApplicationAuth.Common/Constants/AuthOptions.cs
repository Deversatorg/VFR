using Microsoft.IdentityModel.Tokens;
using System;
using System.Text;

namespace ApplicationAuth.Common.Constants
{
    public static class AuthOptions
    {
        public const string DefaultIssuer = "ApplicationAuthAuthServer";
        public const string DefaultAudience = "Client";
        public const int DefaultAccessTokenLifetimeDays = 14;
        public const int DefaultRefreshTokenLifetimeDays = 30;

        public static SigningCredentials GetSigningCredentials(string signingKey)
        {
            return new SigningCredentials(
                GetSymmetricSecurityKey(signingKey),
                SecurityAlgorithms.HmacSha256);
        }

        public static SymmetricSecurityKey GetSymmetricSecurityKey(string signingKey)
        {
            if (string.IsNullOrWhiteSpace(signingKey))
            {
                throw new InvalidOperationException("JWT signing key is not configured.");
            }

            return new SymmetricSecurityKey(Encoding.ASCII.GetBytes(signingKey));
        }
    }
}
