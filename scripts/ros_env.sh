#!/usr/bin/env bash

unset ROS_DISCOVERY_SERVER
unset ROS_SUPER_CLIENT
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:?ROS_DOMAIN_ID is required from the host manifest}"
export ROS_AUTOMATIC_DISCOVERY_RANGE="${ROS_AUTOMATIC_DISCOVERY_RANGE:?ROS_AUTOMATIC_DISCOVERY_RANGE is required from the host manifest}"

TB3_FASTDDS_PROFILE="${TB3_FASTDDS_PROFILE:?TB3_FASTDDS_PROFILE is required from the host manifest}"
if [ ! -s "$TB3_FASTDDS_PROFILE" ]; then
  echo "Fast DDS profile is missing: $TB3_FASTDDS_PROFILE" >&2
  return 1 2>/dev/null || exit 1
fi
export FASTRTPS_DEFAULT_PROFILES_FILE="$TB3_FASTDDS_PROFILE"
export FASTDDS_DEFAULT_PROFILES_FILE="$TB3_FASTDDS_PROFILE"
