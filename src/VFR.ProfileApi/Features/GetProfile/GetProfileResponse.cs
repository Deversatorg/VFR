namespace VFR.ProfileApi.Features.GetProfile;

public class GetProfileResponse
{
    public Guid Id { get; set; }
    public string UserId { get; set; } = string.Empty;
    public double Height { get; set; }
    public double Weight { get; set; }
    public string BodyType { get; set; } = string.Empty;
}
